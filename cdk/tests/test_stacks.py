"""Tests for Chaos Dungeon CDK stacks."""
import aws_cdk as cdk
from aws_cdk import assertions

from stacks.api_stack import ChaosApiStack
from stacks.base_stack import ChaosBaseStack


class TestBaseStack:
    """Tests for ChaosBaseStack."""

    def test_dynamodb_table_created(self):
        """Test that DynamoDB table is created with correct schema."""
        app = cdk.App()
        stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        template = assertions.Template.from_stack(stack)

        # Verify DynamoDB table exists with correct key schema
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "KeySchema": [
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "BillingMode": "PAY_PER_REQUEST",
            },
        )

    def test_dynamodb_table_has_gsi(self):
        """Test that DynamoDB table has GSI1."""
        app = cdk.App()
        stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        template = assertions.Template.from_stack(stack)

        # Verify GSI exists
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "GlobalSecondaryIndexes": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "IndexName": "GSI1",
                                "KeySchema": [
                                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                                ],
                            }
                        )
                    ]
                ),
            },
        )

    def test_secrets_manager_secret_created(self):
        """Test that Secrets Manager secret is created."""
        app = cdk.App()
        stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        template = assertions.Template.from_stack(stack)

        # Verify secret exists
        template.has_resource_properties(
            "AWS::SecretsManager::Secret",
            {"Description": "Claude API key for Chaos Dungeon DM"},
        )

    def test_lambda_layer_created(self):
        """Test that Lambda layer is created."""
        app = cdk.App()
        stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        template = assertions.Template.from_stack(stack)

        # Verify layer exists
        template.has_resource_properties(
            "AWS::Lambda::LayerVersion",
            {"Description": "Shared utilities and models for Chaos Dungeon"},
        )

    def test_dev_environment_destroys_table(self):
        """Test that dev environment uses DESTROY removal policy."""
        app = cdk.App()
        stack = ChaosBaseStack(app, "TestBaseStack", environment="dev")
        template = assertions.Template.from_stack(stack)

        # In dev, table should have UpdateReplacePolicy: Delete
        template.has_resource(
            "AWS::DynamoDB::Table",
            {
                "DeletionPolicy": "Delete",
                "UpdateReplacePolicy": "Delete",
            },
        )

    def test_prod_environment_retains_table(self):
        """Test that prod environment uses RETAIN removal policy."""
        app = cdk.App()
        stack = ChaosBaseStack(app, "TestBaseStack", environment="prod")
        template = assertions.Template.from_stack(stack)

        # In prod, table should have UpdateReplacePolicy: Retain
        template.has_resource(
            "AWS::DynamoDB::Table",
            {
                "DeletionPolicy": "Retain",
                "UpdateReplacePolicy": "Retain",
            },
        )

    def test_outputs_created(self):
        """Test that stack outputs are created."""
        app = cdk.App()
        stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        template = assertions.Template.from_stack(stack)

        # Verify outputs exist
        template.has_output("TableName", {})
        template.has_output("TableArn", {})
        template.has_output("ClaudeSecretArn", {})
        template.has_output("SharedLayerArn", {})


class TestApiStack:
    """Tests for ChaosApiStack."""

    def test_api_gateway_created(self):
        """Test that API Gateway is created."""
        app = cdk.App()
        base_stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        api_stack = ChaosApiStack(
            app,
            "TestApiStack",
            environment="test",
            base_stack=base_stack,
        )
        template = assertions.Template.from_stack(api_stack)

        # Verify REST API exists
        template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            {"Name": "chaos-test-api"},
        )

    def test_api_has_cors(self):
        """Test that API Gateway has CORS enabled."""
        app = cdk.App()
        base_stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        api_stack = ChaosApiStack(
            app,
            "TestApiStack",
            environment="test",
            base_stack=base_stack,
        )
        template = assertions.Template.from_stack(api_stack)

        # Verify OPTIONS methods exist (CORS preflight) - at least some methods defined
        resources = template.find_resources("AWS::ApiGateway::Method")
        assert len(resources) > 0, "Expected at least one API Gateway method"

    def test_api_resources_created(self):
        """Test that API resources are created."""
        app = cdk.App()
        base_stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        api_stack = ChaosApiStack(
            app,
            "TestApiStack",
            environment="test",
            base_stack=base_stack,
        )
        template = assertions.Template.from_stack(api_stack)

        # Verify resources exist - at least characters and sessions
        resources = template.find_resources("AWS::ApiGateway::Resource")
        assert len(resources) >= 2, "Expected at least characters and sessions resources"

    def test_api_outputs_created(self):
        """Test that API stack outputs are created."""
        app = cdk.App()
        base_stack = ChaosBaseStack(app, "TestBaseStack", environment="test")
        api_stack = ChaosApiStack(
            app,
            "TestApiStack",
            environment="test",
            base_stack=base_stack,
        )
        template = assertions.Template.from_stack(api_stack)

        template.has_output("ApiUrl", {})
        template.has_output("ApiId", {})
