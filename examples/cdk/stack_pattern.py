"""
Example CDK stack pattern for Chaos Dungeon.

This demonstrates:
- Standard stack structure
- Resource naming conventions
- Environment-based configuration
- Output exports
"""
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


class ExampleStack(Stack):
    """
    Example stack demonstrating standard patterns.

    This stack creates:
    - DynamoDB table with single-table design
    - Lambda function with proper configuration
    - API Gateway REST API
    - Necessary IAM permissions
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """
        Initialize the stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            environment: Deployment environment (dev/prod)
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment
        self.prefix = f"chaos-{environment}"

        # Create resources
        self.table = self._create_table()
        self.lambda_layer = self._create_lambda_layer()
        self.function = self._create_lambda_function()
        self.api = self._create_api()

        # Grant permissions
        self.table.grant_read_write_data(self.function)

        # Export outputs
        self._create_outputs()

    def _create_table(self) -> dynamodb.Table:
        """Create DynamoDB table with single-table design."""
        table = dynamodb.Table(
            self,
            "Table",
            table_name=f"{self.prefix}-main",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING,
            ),
            # On-demand billing for cost control
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            # Retain table in prod, destroy in dev
            removal_policy=(
                RemovalPolicy.RETAIN
                if self.environment == "prod"
                else RemovalPolicy.DESTROY
            ),
            # Enable point-in-time recovery in prod
            point_in_time_recovery=self.environment == "prod",
        )

        # Add GSI for reverse lookups if needed
        table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK",
                type=dynamodb.AttributeType.STRING,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        return table

    def _create_lambda_layer(self) -> lambda_.LayerVersion:
        """Create Lambda layer for shared code."""
        return lambda_.LayerVersion(
            self,
            "SharedLayer",
            layer_version_name=f"{self.prefix}-shared",
            code=lambda_.Code.from_asset(
                "../lambdas",
                bundling={
                    "image": lambda_.Runtime.PYTHON_3_12.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output/python "
                        "&& cp -r shared /asset-output/python/",
                    ],
                },
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared utilities and models",
        )

    def _create_lambda_function(self) -> lambda_.Function:
        """Create Lambda function with standard configuration."""
        # Log group with retention
        log_group = logs.LogGroup(
            self,
            "FunctionLogs",
            log_group_name=f"/aws/lambda/{self.prefix}-example",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        function = lambda_.Function(
            self,
            "Function",
            function_name=f"{self.prefix}-example",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/example"),
            layers=[self.lambda_layer],
            environment={
                "TABLE_NAME": self.table.table_name,
                "ENVIRONMENT": self.environment,
                "POWERTOOLS_SERVICE_NAME": "chaos-dungeon",
                "POWERTOOLS_LOG_LEVEL": "DEBUG" if self.environment == "dev" else "INFO",
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=lambda_.Tracing.ACTIVE,
            log_group=log_group,
        )

        return function

    def _create_api(self) -> apigw.RestApi:
        """Create API Gateway REST API."""
        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"{self.prefix}-api",
            description="Chaos Dungeon API",
            deploy_options=apigw.StageOptions(
                stage_name=self.environment,
                throttling_rate_limit=100,
                throttling_burst_limit=200,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=(
                    ["https://chaos.jurigregg.com"]
                    if self.environment == "prod"
                    else apigw.Cors.ALL_ORIGINS
                ),
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        # Add Lambda integration
        integration = apigw.LambdaIntegration(
            self.function,
            proxy=True,
        )

        # Add routes
        items = api.root.add_resource("items")
        items.add_method("GET", integration)
        items.add_method("POST", integration)

        item = items.add_resource("{id}")
        item.add_method("GET", integration)
        item.add_method("DELETE", integration)

        return api

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "TableName",
            value=self.table.table_name,
            description="DynamoDB table name",
            export_name=f"{self.prefix}-table-name",
        )

        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name=f"{self.prefix}-api-url",
        )

        CfnOutput(
            self,
            "FunctionArn",
            value=self.function.function_arn,
            description="Lambda function ARN",
            export_name=f"{self.prefix}-function-arn",
        )
