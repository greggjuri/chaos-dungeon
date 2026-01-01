"""API infrastructure stack for Chaos Dungeon.

Contains:
- API Gateway REST API with CORS
- Character Lambda function
- Stage configuration for dev/prod
"""
from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_apigateway as apigw
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

        # Create Lambda functions
        self.character_function = self._create_character_lambda()

        # Create API Gateway
        self.api = self._create_api()

        # Export outputs
        self._create_outputs()

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
            layers=[self.base_stack.shared_layer],
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

        # /sessions endpoint (mock for now, will be implemented in future PRP)
        sessions = api.root.add_resource("sessions")
        sessions.add_method(
            "POST",
            apigw.MockIntegration(
                integration_responses=[
                    apigw.IntegrationResponse(status_code="201")
                ],
                request_templates={"application/json": '{"statusCode": 201}'},
            ),
            method_responses=[apigw.MethodResponse(status_code="201")],
        )

        session = sessions.add_resource("{sessionId}")
        session.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[
                    apigw.IntegrationResponse(status_code="200")
                ],
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[apigw.MethodResponse(status_code="200")],
        )

        # /sessions/{sessionId}/action endpoint
        action = session.add_resource("action")
        action.add_method(
            "POST",
            apigw.MockIntegration(
                integration_responses=[
                    apigw.IntegrationResponse(status_code="200")
                ],
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[apigw.MethodResponse(status_code="200")],
        )

        # /sessions/{sessionId}/history endpoint
        history = session.add_resource("history")
        history.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[
                    apigw.IntegrationResponse(status_code="200")
                ],
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[apigw.MethodResponse(status_code="200")],
        )

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
