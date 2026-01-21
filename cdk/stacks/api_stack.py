"""API infrastructure stack for Chaos Dungeon.

Contains:
- API Gateway REST API with CORS
- Lambda layer for shared Python code
- Character Lambda function
- Session Lambda function
- DM Lambda function (action handler)
- Stage configuration for dev/prod
"""
from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from .base_stack import ChaosBaseStack


class ChaosApiStack(Stack):
    """API infrastructure stack with API Gateway and Lambda functions."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        base_stack: ChaosBaseStack,
        **kwargs,
    ) -> None:
        """Initialize API stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            environment: Deployment environment (dev/prod)
            base_stack: Reference to base infrastructure stack
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        self.deploy_env = environment
        self.prefix = f"chaos-{environment}"
        self.base_stack = base_stack

        # Create Lambda layer first
        self.shared_layer = self._create_lambda_layer()

        # Create Lambda functions
        self.character_function = self._create_character_lambda()
        self.session_function = self._create_session_lambda()
        self.dm_function = self._create_dm_lambda()

        # Create CloudWatch alarms for cost protection
        self._create_cost_alarms()

        # Create API Gateway
        self.api = self._create_api()

        # Export outputs
        self._create_outputs()

    def _create_lambda_layer(self) -> lambda_.LayerVersion:
        """Create Lambda layer for shared Python code and dependencies."""
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
            description="Shared utilities and models for Chaos Dungeon",
        )

    def _create_character_lambda(self) -> lambda_.Function:
        """Create the character handler Lambda function."""
        function = lambda_.Function(
            self,
            "CharacterHandler",
            function_name=f"{self.prefix}-character",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="character.handler.lambda_handler",
            code=lambda_.Code.from_asset(
                "../lambdas",
                exclude=[
                    "tests",
                    "tests/*",
                    "__pycache__",
                    "**/__pycache__",
                    ".pytest_cache",
                    "**/.pytest_cache",
                    ".venv",
                    "venv",
                    "*.pyc",
                    "**/*.pyc",
                    ".ruff_cache",
                    "**/.ruff_cache",
                ],
            ),
            layers=[self.shared_layer],
            environment={
                "TABLE_NAME": self.base_stack.table.table_name,
                "ENVIRONMENT": self.deploy_env,
                "POWERTOOLS_SERVICE_NAME": "character",
                "POWERTOOLS_LOG_LEVEL": (
                    "DEBUG" if self.deploy_env == "dev" else "INFO"
                ),
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB access
        self.base_stack.table.grant_read_write_data(function)

        return function

    def _create_session_lambda(self) -> lambda_.Function:
        """Create the session handler Lambda function."""
        function = lambda_.Function(
            self,
            "SessionHandler",
            function_name=f"{self.prefix}-session",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="session.handler.lambda_handler",
            code=lambda_.Code.from_asset(
                "../lambdas",
                exclude=[
                    "tests",
                    "tests/*",
                    "__pycache__",
                    "**/__pycache__",
                    ".pytest_cache",
                    "**/.pytest_cache",
                    ".venv",
                    "venv",
                    "*.pyc",
                    "**/*.pyc",
                    ".ruff_cache",
                    "**/.ruff_cache",
                ],
            ),
            layers=[self.shared_layer],
            environment={
                "TABLE_NAME": self.base_stack.table.table_name,
                "ENVIRONMENT": self.deploy_env,
                "POWERTOOLS_SERVICE_NAME": "session",
                "POWERTOOLS_LOG_LEVEL": (
                    "DEBUG" if self.deploy_env == "dev" else "INFO"
                ),
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB access
        self.base_stack.table.grant_read_write_data(function)

        return function

    def _create_dm_lambda(self) -> lambda_.Function:
        """Create the DM handler Lambda function for action processing."""
        function = lambda_.Function(
            self,
            "DMHandler",
            function_name=f"{self.prefix}-dm",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="dm.handler.lambda_handler",
            code=lambda_.Code.from_asset(
                "../lambdas",
                exclude=[
                    "tests",
                    "tests/*",
                    "__pycache__",
                    "**/__pycache__",
                    ".pytest_cache",
                    "**/.pytest_cache",
                    ".venv",
                    "venv",
                    "*.pyc",
                    "**/*.pyc",
                    ".ruff_cache",
                    "**/.ruff_cache",
                ],
            ),
            layers=[self.shared_layer],
            environment={
                "TABLE_NAME": self.base_stack.table.table_name,
                "ENVIRONMENT": self.deploy_env,
                "POWERTOOLS_SERVICE_NAME": "dm",
                "POWERTOOLS_METRICS_NAMESPACE": "ChaosDungeon",
                "POWERTOOLS_LOG_LEVEL": (
                    "DEBUG" if self.deploy_env == "dev" else "INFO"
                ),
                # Model provider: "mistral" (Bedrock) or "claude" (Anthropic API)
                "MODEL_PROVIDER": "mistral",
                # Keep Claude API key for rollback capability
                "CLAUDE_API_KEY_PARAM": "/automations/dev/secrets/anthropic_api_key",
            },
            timeout=Duration.seconds(30),  # AI API can be slow
            memory_size=256,
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB access
        self.base_stack.table.grant_read_write_data(function)

        # Grant SSM Parameter Store access for Claude API key (for rollback)
        function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:GetParameter"],
                resources=[
                    "arn:aws:ssm:us-east-1:490004610151:parameter/automations/dev/secrets/anthropic_api_key"
                ],
            )
        )

        # Grant Bedrock model invocation for Mistral
        function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[
                    # Mistral Small in us-east-1
                    "arn:aws:bedrock:us-east-1::foundation-model/mistral.mistral-small-2402-v1:0"
                ],
            )
        )

        return function

    def _create_cost_alarms(self) -> None:
        """Create CloudWatch alarms for cost protection monitoring."""
        # High usage alarm (80% of 500K daily limit = 400K tokens)
        cloudwatch.Alarm(
            self,
            "HighTokenUsageAlarm",
            alarm_name=f"{self.prefix}-high-token-usage",
            metric=cloudwatch.Metric(
                namespace="ChaosDungeon",
                metric_name="TokensConsumed",
                statistic="Sum",
                period=Duration.hours(24),
            ),
            threshold=400_000,  # 80% of 500K daily limit
            evaluation_periods=1,
            alarm_description="Daily token usage approaching 80% of limit (400K/500K)",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # Limit hit alarm - triggers when any limit is hit
        cloudwatch.Alarm(
            self,
            "LimitHitAlarm",
            alarm_name=f"{self.prefix}-limit-hit",
            metric=cloudwatch.Metric(
                namespace="ChaosDungeon",
                metric_name="LimitHits",
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=1,
            alarm_description="Token limit was hit (global or session)",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

    def _create_api(self) -> apigw.RestApi:
        """Create API Gateway REST API with CORS configuration."""
        # Determine CORS origins based on environment
        cors_origins = (
            ["https://chaos.jurigregg.com"]
            if self.deploy_env == "prod"
            else apigw.Cors.ALL_ORIGINS
        )

        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"{self.prefix}-api",
            description="Chaos Dungeon game API",
            deploy_options=apigw.StageOptions(
                stage_name=self.deploy_env,
                throttling_rate_limit=100,
                throttling_burst_limit=200,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=cors_origins,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-User-Id",
                ],
            ),
        )

        # Create Lambda integration for character endpoints
        character_integration = apigw.LambdaIntegration(
            self.character_function,
            proxy=True,
        )

        # /characters endpoint
        characters = api.root.add_resource("characters")
        characters.add_method("GET", character_integration)
        characters.add_method("POST", character_integration)

        # /characters/{characterId} endpoint
        character = characters.add_resource("{characterId}")
        character.add_method("GET", character_integration)
        character.add_method("PATCH", character_integration)
        character.add_method("DELETE", character_integration)

        # Create Lambda integration for session endpoints
        session_integration = apigw.LambdaIntegration(
            self.session_function,
            proxy=True,
        )

        # /sessions endpoint
        sessions = api.root.add_resource("sessions")
        sessions.add_method("GET", session_integration)
        sessions.add_method("POST", session_integration)

        # /sessions/{sessionId} endpoint
        session = sessions.add_resource("{sessionId}")
        session.add_method("GET", session_integration)
        session.add_method("DELETE", session_integration)

        # Create Lambda integration for DM handler
        dm_integration = apigw.LambdaIntegration(
            self.dm_function,
            proxy=True,
        )

        # /sessions/{sessionId}/action endpoint
        action = session.add_resource("action")
        action.add_method("POST", dm_integration)

        # /sessions/{sessionId}/history endpoint
        history = session.add_resource("history")
        history.add_method("GET", session_integration)

        # /sessions/{sessionId}/options endpoint
        options = session.add_resource("options")
        options.add_method("PATCH", session_integration)

        return api

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name=f"{self.prefix}-api-url",
        )

        CfnOutput(
            self,
            "ApiId",
            value=self.api.rest_api_id,
            description="API Gateway ID",
            export_name=f"{self.prefix}-api-id",
        )

        CfnOutput(
            self,
            "CharacterFunctionArn",
            value=self.character_function.function_arn,
            description="Character Lambda function ARN",
            export_name=f"{self.prefix}-character-function-arn",
        )

        CfnOutput(
            self,
            "SessionFunctionArn",
            value=self.session_function.function_arn,
            description="Session Lambda function ARN",
            export_name=f"{self.prefix}-session-function-arn",
        )

        CfnOutput(
            self,
            "SharedLayerArn",
            value=self.shared_layer.layer_version_arn,
            description="Shared Lambda layer ARN",
            export_name=f"{self.prefix}-api-shared-layer-arn",
        )

        CfnOutput(
            self,
            "DMFunctionArn",
            value=self.dm_function.function_arn,
            description="DM Lambda function ARN",
            export_name=f"{self.prefix}-dm-function-arn",
        )
