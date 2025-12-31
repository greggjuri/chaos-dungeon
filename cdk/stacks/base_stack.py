"""Base infrastructure stack for Chaos Dungeon.

Contains:
- DynamoDB table with single-table design
- Secrets Manager secret for Claude API key
- Lambda layer for shared Python code
"""
from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class ChaosBaseStack(Stack):
    """Base infrastructure stack with DynamoDB, Secrets, and Lambda layer."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize base stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            environment: Deployment environment (dev/prod)
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        self.deploy_env = environment
        self.prefix = f"chaos-{environment}"

        # Create resources
        self.table = self._create_table()
        self.claude_secret = self._create_secret()
        self.shared_layer = self._create_lambda_layer()

        # Export outputs
        self._create_outputs()

    def _create_table(self) -> dynamodb.Table:
        """Create DynamoDB table with single-table design."""
        table = dynamodb.Table(
            self,
            "MainTable",
            table_name=f"{self.prefix}-main",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=(
                RemovalPolicy.RETAIN
                if self.deploy_env == "prod"
                else RemovalPolicy.DESTROY
            ),
            point_in_time_recovery=self.deploy_env == "prod",
        )

        # Add GSI for reverse lookups
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

    def _create_secret(self) -> secretsmanager.Secret:
        """Create Secrets Manager secret for Claude API key."""
        return secretsmanager.Secret(
            self,
            "ClaudeApiKey",
            secret_name=f"{self.prefix}/claude-api-key",
            description="Claude API key for Chaos Dungeon DM",
        )

    def _create_lambda_layer(self) -> lambda_.LayerVersion:
        """Create Lambda layer for shared Python code."""
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
            "TableArn",
            value=self.table.table_arn,
            description="DynamoDB table ARN",
            export_name=f"{self.prefix}-table-arn",
        )

        CfnOutput(
            self,
            "ClaudeSecretArn",
            value=self.claude_secret.secret_arn,
            description="Claude API key secret ARN",
            export_name=f"{self.prefix}-claude-secret-arn",
        )

        CfnOutput(
            self,
            "SharedLayerArn",
            value=self.shared_layer.layer_version_arn,
            description="Shared Lambda layer ARN",
            export_name=f"{self.prefix}-shared-layer-arn",
        )
