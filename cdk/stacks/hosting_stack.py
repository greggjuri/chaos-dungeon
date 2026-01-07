"""Hosting stack for frontend deployment at chaos.jurigregg.com.

Contains:
- S3 bucket for frontend static files
- CloudFront distribution with S3 and API Gateway origins
- Route 53 DNS records (A and AAAA)
"""
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .api_stack import ChaosApiStack


class ChaosHostingStack(Stack):
    """Stack for frontend hosting and domain setup."""

    DOMAIN_NAME = "chaos.jurigregg.com"
    HOSTED_ZONE_DOMAIN = "jurigregg.com"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_stack: ChaosApiStack,
        environment: str = "prod",
        certificate_arn: str | None = None,
        **kwargs,
    ) -> None:
        """Initialize hosting stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            api_stack: Reference to API stack for API Gateway origin
            environment: Deployment environment (dev/prod)
            certificate_arn: ARN of wildcard certificate in ACM (us-east-1)
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        self.deploy_env = environment
        self.prefix = f"chaos-{environment}"
        self.api_stack = api_stack

        # Look up existing hosted zone
        self.hosted_zone = route53.HostedZone.from_lookup(
            self,
            "HostedZone",
            domain_name=self.HOSTED_ZONE_DOMAIN,
        )

        # Look up existing wildcard certificate
        if not certificate_arn:
            raise ValueError("certificate_arn is required for HostingStack")

        self.certificate = acm.Certificate.from_certificate_arn(
            self,
            "WildcardCert",
            certificate_arn=certificate_arn,
        )

        # Create resources
        self.bucket = self._create_s3_bucket()
        self.distribution = self._create_cloudfront_distribution()
        self._create_dns_records()
        self._create_outputs()

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

    def _create_cloudfront_distribution(self) -> cloudfront.Distribution:
        """Create CloudFront distribution with S3 and API Gateway origins."""
        # S3 origin with Origin Access Control
        s3_origin = origins.S3BucketOrigin.with_origin_access_control(self.bucket)

        # API Gateway origin
        api_domain = (
            f"{self.api_stack.api.rest_api_id}"
            f".execute-api.{self.region}.amazonaws.com"
        )
        api_origin = origins.HttpOrigin(
            api_domain,
            origin_path=f"/{self.api_stack.deploy_env}",
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

        # Origin request policy for API (forward headers to origin)
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
