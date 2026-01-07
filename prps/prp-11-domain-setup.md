# PRP-11: Domain Setup and Production Deployment

**Created**: 2026-01-07
**Initial**: `initials/init-11-domain-setup.md`
**Status**: Complete

---

## Overview

### Problem Statement
The Chaos Dungeon game needs to be deployed to production at `chaos.jurigregg.com`. Currently, the frontend runs locally and the backend is deployed to API Gateway with a generated URL. Users need a permanent, memorable URL to access the game.

### Proposed Solution
Create a new CDK `HostingStack` that provisions:
- S3 bucket for frontend static files
- CloudFront distribution with the S3 bucket and API Gateway as origins
- Route 53 DNS records pointing to CloudFront
- Use the existing wildcard certificate for SSL/TLS

Architecture: Single domain where `chaos.jurigregg.com/` serves the frontend and `chaos.jurigregg.com/api/*` proxies to API Gateway (no CORS issues).

### Success Criteria
- [ ] `cdk synth` succeeds for hosting stack
- [ ] S3 bucket created with proper access controls (OAC, no public access)
- [ ] CloudFront distribution serves frontend at `chaos.jurigregg.com`
- [ ] API requests to `/api/*` route correctly to API Gateway
- [ ] SSL/TLS working with wildcard cert
- [ ] SPA routing works (deep links return index.html)
- [ ] Frontend deployment script works
- [ ] Cache invalidation works
- [ ] Site loads in under 3 seconds
- [ ] All existing functionality works on production domain

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview, cost budget
- `docs/DECISIONS.md` - ADR-002 (AWS Serverless), ADR-008 (React + Vite)
- `initials/init-11-domain-setup.md` - Full specification

### Dependencies
- **Required**:
  - init-10-cost-protection (completed) - Cost limits must be in place before going live
  - Working backend (API Gateway + Lambda) - Completed
  - Working frontend (React build) - Completed
  - Existing wildcard certificate for `*.jurigregg.com` in ACM (us-east-1)
  - Existing Route 53 hosted zone for `jurigregg.com`

### Files to Modify/Create
```
cdk/stacks/hosting_stack.py       # NEW - S3, CloudFront, Route 53
cdk/app.py                        # MODIFY - Add HostingStack
frontend/vite.config.ts           # MODIFY - Add dev proxy configuration
scripts/deploy-frontend.sh        # NEW - Frontend deployment script
```

---

## Technical Specification

### Architecture

```
Browser → chaos.jurigregg.com
              ↓
         CloudFront Distribution
              ↓
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
  /api/*             /* (default)
    │                   │
    ▼                   ▼
API Gateway          S3 Bucket
(chaos-prod-api)   (chaos-prod-frontend)
```

### CloudFront Behaviors

| Path Pattern | Origin | Cache Policy | Notes |
|-------------|--------|--------------|-------|
| `/api/*` | API Gateway | No cache | Forward all headers/query strings |
| `*` (default) | S3 | Long cache for assets | SPA error handling for 404/403 |

### S3 Bucket Configuration
- Block all public access
- CloudFront Origin Access Control (OAC) for secure access
- Versioning enabled for rollback
- S3-managed encryption

### DNS Records
| Type | Name | Target |
|------|------|--------|
| A | chaos.jurigregg.com | CloudFront distribution (alias) |
| AAAA | chaos.jurigregg.com | CloudFront distribution (alias) |

---

## Implementation Steps

### Step 1: Create HostingStack CDK Module
**Files**: `cdk/stacks/hosting_stack.py`

Create a new CDK stack for frontend hosting with S3, CloudFront, and Route 53.

```python
"""Hosting stack for frontend deployment at chaos.jurigregg.com."""
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from constructs import Construct


class ChaosHostingStack(Stack):
    """Stack for frontend hosting and domain setup."""

    DOMAIN_NAME = "chaos.jurigregg.com"
    HOSTED_ZONE_DOMAIN = "jurigregg.com"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_stack,
        environment: str = "prod",
        certificate_arn: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.deploy_env = environment
        self.prefix = f"chaos-{environment}"

        # Look up existing hosted zone
        self.hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=self.HOSTED_ZONE_DOMAIN,
        )

        # Look up existing wildcard certificate
        if not certificate_arn:
            raise ValueError("certificate_arn is required for HostingStack")

        self.certificate = acm.Certificate.from_certificate_arn(
            self, "WildcardCert",
            certificate_arn=certificate_arn,
        )

        # Create resources
        self.bucket = self._create_s3_bucket()
        self.distribution = self._create_cloudfront_distribution(api_stack)
        self._create_dns_records()
        self._create_outputs()
```

**Validation**:
- [ ] Stack synthesizes without errors
- [ ] Lint passes

### Step 2: Implement S3 Bucket Creation
**Files**: `cdk/stacks/hosting_stack.py`

Add the S3 bucket creation method.

```python
def _create_s3_bucket(self) -> s3.Bucket:
    """Create S3 bucket for frontend static files."""
    return s3.Bucket(
        self,
        "FrontendBucket",
        bucket_name=f"{self.prefix}-frontend",
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        versioned=True,
        removal_policy=(
            RemovalPolicy.DESTROY
            if self.deploy_env == "dev"
            else RemovalPolicy.RETAIN
        ),
        auto_delete_objects=self.deploy_env == "dev",
        encryption=s3.BucketEncryption.S3_MANAGED,
    )
```

**Validation**:
- [ ] Bucket has no public access
- [ ] Versioning enabled

### Step 3: Implement CloudFront Distribution
**Files**: `cdk/stacks/hosting_stack.py`

Add the CloudFront distribution with S3 and API Gateway origins.

```python
def _create_cloudfront_distribution(self, api_stack) -> cloudfront.Distribution:
    """Create CloudFront distribution with S3 and API Gateway origins."""

    # S3 origin with Origin Access Control
    s3_origin = origins.S3BucketOrigin.with_origin_access_control(
        self.bucket
    )

    # API Gateway origin
    api_domain = f"{api_stack.api.rest_api_id}.execute-api.{self.region}.amazonaws.com"
    api_origin = origins.HttpOrigin(
        api_domain,
        origin_path=f"/{api_stack.deploy_env}",
        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
    )

    # Cache policy for API (no caching, forward headers)
    api_cache_policy = cloudfront.CachePolicy(
        self,
        "ApiCachePolicy",
        cache_policy_name=f"{self.prefix}-api-no-cache",
        default_ttl=Duration.seconds(0),
        max_ttl=Duration.seconds(0),
        min_ttl=Duration.seconds(0),
        query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
        header_behavior=cloudfront.CacheHeaderBehavior.allow_list(
            "Content-Type",
            "X-User-Id",
        ),
        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
    )

    # Origin request policy for API
    api_origin_request_policy = cloudfront.OriginRequestPolicy(
        self,
        "ApiOriginRequestPolicy",
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
            cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
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
        domain_names=[self.DOMAIN_NAME],
        certificate=self.certificate,
        default_root_object="index.html",
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
        price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        http_version=cloudfront.HttpVersion.HTTP2_AND_3,
    )

    return distribution
```

**Validation**:
- [ ] Distribution has two origins (S3 + API Gateway)
- [ ] API path pattern `/api/*` configured
- [ ] SPA error handling for 404/403

### Step 4: Implement DNS Records
**Files**: `cdk/stacks/hosting_stack.py`

Add Route 53 DNS record creation.

```python
def _create_dns_records(self) -> None:
    """Create Route 53 DNS records pointing to CloudFront."""

    # A record for IPv4
    route53.ARecord(
        self,
        "AliasRecord",
        zone=self.hosted_zone,
        record_name="chaos",
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

**Validation**:
- [ ] A record created
- [ ] AAAA record created

### Step 5: Add Stack Outputs
**Files**: `cdk/stacks/hosting_stack.py`

Add CloudFormation outputs for deployment scripts.

```python
def _create_outputs(self) -> None:
    """Create CloudFormation outputs."""

    CfnOutput(
        self,
        "SiteUrl",
        value=f"https://{self.DOMAIN_NAME}",
        description="Website URL",
        export_name=f"{self.prefix}-site-url",
    )

    CfnOutput(
        self,
        "DistributionId",
        value=self.distribution.distribution_id,
        description="CloudFront distribution ID (for cache invalidation)",
        export_name=f"{self.prefix}-distribution-id",
    )

    CfnOutput(
        self,
        "BucketName",
        value=self.bucket.bucket_name,
        description="S3 bucket name for frontend deployment",
        export_name=f"{self.prefix}-frontend-bucket",
    )

    CfnOutput(
        self,
        "DistributionDomainName",
        value=self.distribution.distribution_domain_name,
        description="CloudFront distribution domain name",
        export_name=f"{self.prefix}-distribution-domain",
    )
```

**Validation**:
- [ ] All outputs exported

### Step 6: Update CDK App Entry Point
**Files**: `cdk/app.py`

Add the HostingStack to the CDK app, only for prod environment.

```python
#!/usr/bin/env python3
"""CDK app entry point for Chaos Dungeon."""
import os

import aws_cdk as cdk

from stacks.api_stack import ChaosApiStack
from stacks.base_stack import ChaosBaseStack
from stacks.hosting_stack import ChaosHostingStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

environment = app.node.try_get_context("environment") or "dev"

# Certificate ARN for wildcard cert (required for hosting stack)
certificate_arn = app.node.try_get_context("certificateArn")

base_stack = ChaosBaseStack(
    app,
    f"ChaosBase-{environment}",
    environment=environment,
    env=env,
)

api_stack = ChaosApiStack(
    app,
    f"ChaosApi-{environment}",
    environment=environment,
    base_stack=base_stack,
    env=env,
)

# Only create hosting stack for prod (or when explicitly enabled)
if environment == "prod" or os.environ.get("ENABLE_HOSTING") == "true":
    if not certificate_arn:
        raise ValueError(
            "certificateArn context is required for hosting stack. "
            "Use: cdk deploy -c certificateArn=arn:aws:acm:..."
        )

    hosting_stack = ChaosHostingStack(
        app,
        f"ChaosHosting-{environment}",
        api_stack=api_stack,
        environment=environment,
        certificate_arn=certificate_arn,
        env=env,
    )

app.synth()
```

**Validation**:
- [ ] `cdk synth -c environment=prod -c certificateArn=xxx` works
- [ ] Hosting stack not created for dev environment

### Step 7: Update Vite Config for Development Proxy
**Files**: `frontend/vite.config.ts`

Add proxy configuration for local development to route `/api` requests to API Gateway.

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'https://xxxxx.execute-api.us-east-1.amazonaws.com/dev',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        secure: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
```

Note: The API URL should be set in `.env.local` or passed via environment variable.

**Validation**:
- [ ] `npm run dev` starts without errors
- [ ] `/api/characters` proxies to API Gateway

### Step 8: Create Frontend Deployment Script
**Files**: `scripts/deploy-frontend.sh`

Create a script to build and deploy the frontend to S3 with proper cache headers.

```bash
#!/bin/bash
set -e

# Configuration - get from CloudFormation outputs
STACK_NAME="${STACK_NAME:-ChaosHosting-prod}"

echo "Getting deployment configuration from stack: $STACK_NAME"

BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
  --output text)

if [ -z "$BUCKET_NAME" ] || [ "$BUCKET_NAME" == "None" ]; then
  echo "Error: Could not get bucket name from stack outputs"
  exit 1
fi

if [ -z "$DISTRIBUTION_ID" ] || [ "$DISTRIBUTION_ID" == "None" ]; then
  echo "Error: Could not get distribution ID from stack outputs"
  exit 1
fi

echo "Deploying to bucket: $BUCKET_NAME"
echo "CloudFront distribution: $DISTRIBUTION_ID"

# Build frontend
echo "Building frontend..."
cd frontend
npm ci
npm run build
cd ..

# Sync to S3 with appropriate cache headers
echo "Uploading to S3..."

# HTML files - no cache (always fetch fresh for SPA routing)
aws s3 sync frontend/dist/ "s3://$BUCKET_NAME/" \
  --exclude "*" \
  --include "*.html" \
  --cache-control "no-cache, no-store, must-revalidate"

# JS/CSS files - long cache (Vite adds content hashes)
aws s3 sync frontend/dist/ "s3://$BUCKET_NAME/" \
  --exclude "*.html" \
  --include "*.js" \
  --include "*.css" \
  --cache-control "public, max-age=31536000, immutable"

# Other assets (images, fonts, etc.)
aws s3 sync frontend/dist/ "s3://$BUCKET_NAME/" \
  --exclude "*.html" \
  --exclude "*.js" \
  --exclude "*.css" \
  --cache-control "public, max-age=86400"

# Invalidate CloudFront cache for HTML and root
echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/index.html" "/" \
  --no-cli-pager

echo ""
echo "Deployment complete!"
echo "Site: https://chaos.jurigregg.com"
```

**Validation**:
- [ ] Script is executable (`chmod +x`)
- [ ] Script completes without errors
- [ ] Files appear in S3 with correct cache headers

---

## Testing Requirements

### Unit Tests
No new unit tests required - this is infrastructure-only.

### CDK Tests
- Test that hosting stack synthesizes correctly
- Test that S3 bucket has correct properties
- Test that CloudFront distribution has correct behaviors

### Manual Testing
1. Deploy infrastructure: `cd cdk && cdk deploy -c environment=prod -c certificateArn=xxx`
2. Deploy frontend: `./scripts/deploy-frontend.sh`
3. Verify site loads at `https://chaos.jurigregg.com`
4. Verify API calls work via `/api/*` path
5. Test SPA routing (navigate to `/game/xxx` directly)

---

## Integration Test Plan

### Prerequisites
- Backend deployed: `cd cdk && cdk deploy ChaosBase-prod ChaosApi-prod`
- Hosting stack deployed: `cd cdk && cdk deploy ChaosHosting-prod`
- Frontend deployed: `./scripts/deploy-frontend.sh`
- Browser with DevTools open

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Open `https://chaos.jurigregg.com` | Age gate page loads | ☐ |
| 2 | Complete age verification | Redirected to home page | ☐ |
| 3 | Create a new character | Character created, API call to `/api/characters` succeeds | ☐ |
| 4 | Start a game session | Session created, opening message displays | ☐ |
| 5 | Send a player action | DM responds, no CORS errors | ☐ |
| 6 | Reload page | Session persists, game state restored | ☐ |
| 7 | Navigate directly to `/game/{sessionId}` | Game loads correctly (SPA routing) | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Invalid session | Navigate to `/game/nonexistent` | "Session not found" error page | ☐ |
| API error | Disconnect network | Error toast displays | ☐ |
| Token limit | Exhaust daily limit | Narrative limit message | ☐ |

### Browser Checks
- [ ] No CORS errors in Console
- [ ] No JavaScript errors in Console
- [ ] API requests to `/api/*` visible in Network tab
- [ ] Responses are 2xx (not 4xx/5xx)
- [ ] localStorage values persist after refresh
- [ ] HTTPS padlock shows in address bar

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Certificate not found | Wrong ARN or region | Fail CDK deploy with clear message |
| Hosted zone not found | Wrong domain | Fail CDK synth with lookup error |
| Bucket already exists | Name conflict | Use unique prefix per environment |

### Edge Cases
- CloudFront takes 15-30 minutes to deploy initially - this is normal
- DNS propagation may take a few minutes after deployment
- Cache invalidation has a small cost after first 1000 paths/month

---

## Cost Impact

### AWS Services
| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| S3 | ~$0.10 | Minimal storage |
| CloudFront | ~$0.50-1.00 | Low traffic, PRICE_CLASS_100 |
| Route 53 | $0.50 | Hosted zone (already exists) |
| **Total** | ~$1-2/month | Within budget |

---

## Open Questions

1. ~~Single domain vs split domain?~~ - Resolved: Single domain (Option A) per init spec
2. Certificate ARN needs to be obtained from ACM console before deployment

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Well-defined in init spec |
| Feasibility | 9 | Standard AWS CDK patterns |
| Completeness | 9 | All components covered |
| Alignment | 10 | Matches project goals and budget |
| **Overall** | 9 | Ready for implementation |

---

## Pre-Deployment Checklist

Before running `/execute-prp`:

- [ ] Find wildcard certificate ARN from ACM console (us-east-1)
  - AWS Console → Certificate Manager → us-east-1 → `*.jurigregg.com`
- [ ] Verify Route 53 hosted zone exists for `jurigregg.com`
- [ ] Ensure `cdk bootstrap` has been run for the account/region
- [ ] Test frontend build succeeds locally (`cd frontend && npm run build`)

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
