# init-11-domain-setup

## Overview

Deploy Chaos Dungeon to production at `chaos.jurigregg.com`. This includes S3 bucket for frontend static files, CloudFront distribution with SSL, API Gateway custom domain, and Route 53 DNS records.

## Dependencies

- init-10-cost-protection (cost limits in place before going live)
- Existing wildcard certificate for `*.jurigregg.com` in ACM (us-east-1)
- Existing Route 53 hosted zone for `jurigregg.com`
- Working backend (API Gateway + Lambda)
- Working frontend (React build)

## Goals

1. **Frontend hosting** — S3 + CloudFront at `chaos.jurigregg.com`
2. **API routing** — API Gateway at `api.chaos.jurigregg.com` or `/api` path on same domain
3. **SSL/TLS** — Use existing wildcard cert for HTTPS
4. **Cache optimization** — CloudFront caching for static assets
5. **Zero-downtime deployment** — Ability to update without breaking live site
6. **Budget** — Stay within $1-2/month for hosting (per PLANNING.md)

## Architecture Decision: Single Domain vs Split

**Option A: Single Domain (Recommended)**
```
chaos.jurigregg.com/          → CloudFront → S3 (frontend)
chaos.jurigregg.com/api/*     → CloudFront → API Gateway
```
- Simpler CORS (same origin)
- Single CloudFront distribution
- One DNS record

**Option B: Split Domains**
```
chaos.jurigregg.com           → CloudFront → S3 (frontend)
api.chaos.jurigregg.com       → API Gateway custom domain
```
- Requires CORS configuration
- Two DNS records
- More traditional API separation

**Decision**: Use Option A (single domain) for simplicity and to avoid CORS issues.

## Implementation Steps

### Step 1: Look Up Existing Resources

First, we need to reference existing AWS resources:

```python
# cdk/stacks/hosting_stack.py

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_s3_deployment as s3_deploy,
    CfnOutput,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class HostingStack(Stack):
    """Stack for frontend hosting and domain setup."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_stack,  # Reference to ApiStack for API Gateway
        deploy_env: str = "prod",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.deploy_env = deploy_env
        self.prefix = f"chaos-{deploy_env}"
        self.domain_name = "chaos.jurigregg.com"
        self.hosted_zone_domain = "jurigregg.com"
        
        # Look up existing hosted zone
        self.hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=self.hosted_zone_domain
        )
        
        # Look up existing wildcard certificate (must be in us-east-1 for CloudFront)
        self.certificate = acm.Certificate.from_certificate_arn(
            self, "WildcardCert",
            certificate_arn="arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID"
            # TODO: Replace with actual cert ARN or use environment variable
        )
        
        # Create resources
        self.bucket = self._create_s3_bucket()
        self.distribution = self._create_cloudfront_distribution(api_stack)
        self._create_dns_records()
        self._create_outputs()
```

### Step 2: Create S3 Bucket for Frontend

```python
def _create_s3_bucket(self) -> s3.Bucket:
    """Create S3 bucket for frontend static files."""
    
    bucket = s3.Bucket(
        self,
        "FrontendBucket",
        bucket_name=f"{self.prefix}-frontend",
        # Block all public access - CloudFront will use OAC
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        # Enable versioning for rollback capability
        versioned=True,
        # Auto-delete objects when stack is destroyed (dev only)
        removal_policy=RemovalPolicy.DESTROY if self.deploy_env == "dev" else RemovalPolicy.RETAIN,
        auto_delete_objects=self.deploy_env == "dev",
        # Enable server-side encryption
        encryption=s3.BucketEncryption.S3_MANAGED,
    )
    
    return bucket
```

### Step 3: Create CloudFront Distribution

```python
def _create_cloudfront_distribution(self, api_stack) -> cloudfront.Distribution:
    """Create CloudFront distribution with S3 and API Gateway origins."""
    
    # Origin Access Control for S3
    oac = cloudfront.S3OriginAccessControl(
        self, "OAC",
        signing=cloudfront.Signing.SIGV4_ALWAYS
    )
    
    # S3 origin for frontend
    s3_origin = origins.S3BucketOrigin.with_origin_access_control(
        self.bucket,
        origin_access_control=oac
    )
    
    # API Gateway origin
    # Extract API Gateway domain from the API URL
    api_domain = f"{api_stack.api.rest_api_id}.execute-api.{self.region}.amazonaws.com"
    api_origin = origins.HttpOrigin(
        api_domain,
        origin_path=f"/{api_stack.api.deployment_stage.stage_name}",
        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
    )
    
    # Cache policy for static assets (long cache)
    static_cache_policy = cloudfront.CachePolicy(
        self, "StaticCachePolicy",
        cache_policy_name=f"{self.prefix}-static-cache",
        default_ttl=Duration.days(1),
        max_ttl=Duration.days(365),
        min_ttl=Duration.seconds(0),
        enable_accept_encoding_gzip=True,
        enable_accept_encoding_brotli=True,
    )
    
    # Cache policy for API (no caching)
    api_cache_policy = cloudfront.CachePolicy(
        self, "ApiCachePolicy",
        cache_policy_name=f"{self.prefix}-api-no-cache",
        default_ttl=Duration.seconds(0),
        max_ttl=Duration.seconds(0),
        min_ttl=Duration.seconds(0),
        # Forward all query strings and headers needed by API
        query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
        header_behavior=cloudfront.CacheHeaderBehavior.allow_list(
            "Authorization",
            "Content-Type",
            "X-User-Id",
        ),
        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
    )
    
    # Origin request policy for API (forward headers)
    api_origin_request_policy = cloudfront.OriginRequestPolicy(
        self, "ApiOriginRequestPolicy",
        origin_request_policy_name=f"{self.prefix}-api-origin-request",
        header_behavior=cloudfront.OriginRequestHeaderBehavior.allow_list(
            "Content-Type",
            "X-User-Id",
        ),
        query_string_behavior=cloudfront.OriginRequestQueryStringBehavior.all(),
        cookie_behavior=cloudfront.OriginRequestCookieBehavior.none(),
    )
    
    # Create distribution
    distribution = cloudfront.Distribution(
        self,
        "Distribution",
        default_behavior=cloudfront.BehaviorOptions(
            origin=s3_origin,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            cache_policy=static_cache_policy,
            # Handle SPA routing - return index.html for 404s
            response_headers_policy=cloudfront.ResponseHeadersPolicy.CORS_ALLOW_ALL_ORIGINS_WITH_PREFLIGHT,
        ),
        additional_behaviors={
            "/api/*": cloudfront.BehaviorOptions(
                origin=api_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=api_cache_policy,
                origin_request_policy=api_origin_request_policy,
            ),
        },
        domain_names=[self.domain_name],
        certificate=self.certificate,
        default_root_object="index.html",
        # Handle SPA routing - custom error response
        error_responses=[
            cloudfront.ErrorResponse(
                http_status=404,
                response_http_status=200,
                response_page_path="/index.html",
                ttl=Duration.seconds(0),
            ),
            cloudfront.ErrorResponse(
                http_status=403,
                response_http_status=200,
                response_page_path="/index.html",
                ttl=Duration.seconds(0),
            ),
        ],
        price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # Cheapest - US, Canada, Europe
        http_version=cloudfront.HttpVersion.HTTP2_AND_3,
    )
    
    # Grant CloudFront read access to S3 bucket
    self.bucket.grant_read(distribution)
    
    return distribution
```

### Step 4: Create DNS Records

```python
def _create_dns_records(self) -> None:
    """Create Route 53 DNS records pointing to CloudFront."""
    
    # A record for IPv4
    route53.ARecord(
        self,
        "AliasRecord",
        zone=self.hosted_zone,
        record_name="chaos",  # Results in chaos.jurigregg.com
        target=route53.RecordTarget.from_alias(
            targets.CloudFrontTarget(self.distribution)
        ),
    )
    
    # AAAA record for IPv6
    route53.AaaaRecord(
        self,
        "AliasRecordIPv6",
        zone=self.hosted_zone,
        record_name="chaos",
        target=route53.RecordTarget.from_alias(
            targets.CloudFrontTarget(self.distribution)
        ),
    )
```

### Step 5: Create Stack Outputs

```python
def _create_outputs(self) -> None:
    """Create CloudFormation outputs."""
    
    CfnOutput(
        self,
        "SiteUrl",
        value=f"https://{self.domain_name}",
        description="Website URL",
    )
    
    CfnOutput(
        self,
        "DistributionId",
        value=self.distribution.distribution_id,
        description="CloudFront distribution ID (for cache invalidation)",
    )
    
    CfnOutput(
        self,
        "BucketName",
        value=self.bucket.bucket_name,
        description="S3 bucket name for frontend deployment",
    )
    
    CfnOutput(
        self,
        "DistributionDomainName",
        value=self.distribution.distribution_domain_name,
        description="CloudFront distribution domain name",
    )
```

### Step 6: Update CDK App Entry Point

Update `cdk/app.py`:

```python
#!/usr/bin/env python3
import os
from aws_cdk import App, Environment

from stacks.base_stack import BaseStack
from stacks.api_stack import ApiStack
from stacks.hosting_stack import HostingStack

app = App()

# Environment configuration
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

deploy_env = os.environ.get("DEPLOY_ENV", "dev")

# Create stacks
base_stack = BaseStack(
    app, f"ChaosBase-{deploy_env}",
    deploy_env=deploy_env,
    env=env,
)

api_stack = ApiStack(
    app, f"ChaosApi-{deploy_env}",
    base_stack=base_stack,
    deploy_env=deploy_env,
    env=env,
)

# Only create hosting stack for prod (or when explicitly enabled)
if deploy_env == "prod" or os.environ.get("ENABLE_HOSTING") == "true":
    hosting_stack = HostingStack(
        app, f"ChaosHosting-{deploy_env}",
        api_stack=api_stack,
        deploy_env=deploy_env,
        env=env,
    )

app.synth()
```

### Step 7: Update Frontend API Configuration

Update `frontend/src/config.ts`:

```typescript
// API configuration based on environment
const isDevelopment = import.meta.env.DEV;

export const config = {
  // In development, use local proxy or direct API Gateway URL
  // In production, use relative path (same domain via CloudFront)
  apiBaseUrl: isDevelopment 
    ? import.meta.env.VITE_API_URL || 'http://localhost:3000/api'
    : '/api',
};
```

Update `frontend/vite.config.ts` for local development proxy:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'https://YOUR_API_GATEWAY_URL',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
```

### Step 8: Create Deployment Script

Create `scripts/deploy-frontend.sh`:

```bash
#!/bin/bash
set -e

# Configuration
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name ChaosHosting-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name ChaosHosting-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
  --output text)

echo "Deploying to bucket: $BUCKET_NAME"
echo "CloudFront distribution: $DISTRIBUTION_ID"

# Build frontend
cd frontend
npm ci
npm run build

# Sync to S3 with appropriate cache headers
# HTML files - no cache (always fetch fresh)
aws s3 sync dist/ s3://$BUCKET_NAME/ \
  --exclude "*" \
  --include "*.html" \
  --cache-control "no-cache, no-store, must-revalidate"

# JS/CSS files - long cache (hashed filenames)
aws s3 sync dist/ s3://$BUCKET_NAME/ \
  --exclude "*.html" \
  --include "*.js" \
  --include "*.css" \
  --cache-control "public, max-age=31536000, immutable"

# Other assets
aws s3 sync dist/ s3://$BUCKET_NAME/ \
  --exclude "*.html" \
  --exclude "*.js" \
  --exclude "*.css" \
  --cache-control "public, max-age=86400"

# Invalidate CloudFront cache for HTML files
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/index.html" "/"

echo "Deployment complete!"
echo "Site: https://chaos.jurigregg.com"
```

### Step 9: Update API Gateway CORS (If Needed)

The current CORS configuration allows `chaos.jurigregg.com`. Verify in `cdk/stacks/api_stack.py`:

```python
# CORS should include production domain
cors_options = apigw.CorsOptions(
    allow_origins=[
        "http://localhost:5173",      # Vite dev server
        "http://localhost:3000",      # Alternative dev
        "https://chaos.jurigregg.com" # Production
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-User-Id", "Authorization"],
)
```

## Pre-Deployment Checklist

Before deploying:

1. [ ] Find and record the wildcard certificate ARN from ACM console (us-east-1)
2. [ ] Verify Route 53 hosted zone exists for `jurigregg.com`
3. [ ] Ensure `cdk bootstrap` has been run for the account/region
4. [ ] Test frontend build succeeds locally (`npm run build`)
5. [ ] Verify cost protection is working (init-10)

## Deployment Steps

```bash
# 1. Set certificate ARN (find in ACM console)
export CERTIFICATE_ARN="arn:aws:acm:us-east-1:ACCOUNT:certificate/ID"

# 2. Deploy infrastructure
cd cdk
DEPLOY_ENV=prod cdk deploy ChaosHosting-prod --require-approval never

# 3. Deploy frontend
cd ..
./scripts/deploy-frontend.sh

# 4. Verify site is live
curl -I https://chaos.jurigregg.com
```

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `cdk/stacks/hosting_stack.py` | CREATE | S3, CloudFront, Route 53 setup |
| `cdk/app.py` | MODIFY | Add HostingStack |
| `cdk/requirements.txt` | MODIFY | Add any new CDK dependencies |
| `frontend/src/config.ts` | CREATE | API URL configuration |
| `frontend/vite.config.ts` | MODIFY | Add dev proxy |
| `scripts/deploy-frontend.sh` | CREATE | Frontend deployment script |
| `cdk/stacks/api_stack.py` | MODIFY | Verify CORS includes prod domain |

## Acceptance Criteria

- [ ] `cdk synth` succeeds for hosting stack
- [ ] S3 bucket created with proper access controls
- [ ] CloudFront distribution serves frontend at `chaos.jurigregg.com`
- [ ] API requests to `/api/*` route correctly to API Gateway
- [ ] SSL/TLS working with wildcard cert
- [ ] SPA routing works (deep links return index.html)
- [ ] Frontend deployment script works
- [ ] Cache invalidation works
- [ ] Site loads in under 3 seconds
- [ ] All existing functionality works on production domain

## Rollback Plan

If issues occur:

1. **DNS rollback**: Delete Route 53 records, traffic stops going to CloudFront
2. **CloudFront disable**: Disable distribution in console
3. **Full rollback**: `cdk destroy ChaosHosting-prod`

Frontend is stateless, so rollback is safe. Game state is in DynamoDB (separate stack).

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| S3 | ~$0.10 (minimal storage) |
| CloudFront | ~$0.50-1.00 (low traffic) |
| Route 53 | $0.50 (hosted zone) |
| **Total** | ~$1-2/month |

Within the $1-2/month budget allocated in PLANNING.md.

## Post-Deployment

After successful deployment:

1. Update `docs/TASK.md` to mark init-11 complete
2. Update `README.md` to remove "(coming soon)" from live URL
3. Add ADR-011 to `docs/DECISIONS.md` documenting hosting decisions
4. Test with a few players before wider announcement

## Out of Scope

- CI/CD pipeline (future enhancement)
- Multiple environments (dev/staging/prod)
- Custom error pages (use default CloudFront errors for now)
- WAF/Shield protection (add if needed later)
- Access logging (add if needed for debugging)

## Notes

- CloudFront can take 15-30 minutes to deploy initially
- Certificate must be in us-east-1 for CloudFront (even if other resources are elsewhere)
- Cache invalidation has a cost ($0.005 per path after first 1000/month)
- The `/api/*` path rewrite removes `/api` prefix before forwarding to API Gateway
