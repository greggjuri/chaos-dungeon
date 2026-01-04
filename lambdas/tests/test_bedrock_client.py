"""Tests for Bedrock client."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from dm.bedrock_client import MODEL_ID, BedrockClient


class TestBedrockClient:
    """Tests for BedrockClient."""

    @patch("dm.bedrock_client.boto3")
    def test_invoke_mistral_success(self, mock_boto3: MagicMock) -> None:
        """Test successful Mistral invocation."""
        mock_bedrock = MagicMock()
        mock_boto3.client.return_value = mock_bedrock

        # Mock response
        response_body = json.dumps({"outputs": [{"text": "The goblin attacks!"}]})
        mock_bedrock.invoke_model.return_value = {
            "body": BytesIO(response_body.encode())
        }

        client = BedrockClient()
        result = client.invoke_mistral("Test prompt")

        assert result == "The goblin attacks!"
        mock_bedrock.invoke_model.assert_called_once()

        # Verify model ID
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        assert call_kwargs["modelId"] == MODEL_ID

    @patch("dm.bedrock_client.boto3")
    def test_invoke_mistral_with_parameters(self, mock_boto3: MagicMock) -> None:
        """Test that parameters are passed correctly."""
        mock_bedrock = MagicMock()
        mock_boto3.client.return_value = mock_bedrock

        response_body = json.dumps({"outputs": [{"text": "Response"}]})
        mock_bedrock.invoke_model.return_value = {
            "body": BytesIO(response_body.encode())
        }

        client = BedrockClient()
        client.invoke_mistral(
            prompt="Test prompt",
            max_tokens=500,
            temperature=0.5,
            top_p=0.9,
        )

        # Verify body parameters
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        body = json.loads(call_kwargs["body"])
        assert body["prompt"] == "Test prompt"
        assert body["max_tokens"] == 500
        assert body["temperature"] == 0.5
        assert body["top_p"] == 0.9

    @patch("dm.bedrock_client.boto3")
    def test_invoke_mistral_client_error(self, mock_boto3: MagicMock) -> None:
        """Test that ClientError is raised on API error."""
        mock_bedrock = MagicMock()
        mock_boto3.client.return_value = mock_bedrock

        mock_bedrock.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate limited"}},
            "InvokeModel",
        )

        client = BedrockClient()

        with pytest.raises(ClientError) as exc_info:
            client.invoke_mistral("Test prompt")

        assert exc_info.value.response["Error"]["Code"] == "ThrottlingException"

    @patch("dm.bedrock_client.boto3")
    def test_send_action_builds_mistral_prompt(self, mock_boto3: MagicMock) -> None:
        """Test that send_action builds Mistral-formatted prompt."""
        mock_bedrock = MagicMock()
        mock_boto3.client.return_value = mock_bedrock

        response_body = json.dumps({"outputs": [{"text": "You attack the goblin."}]})
        mock_bedrock.invoke_model.return_value = {
            "body": BytesIO(response_body.encode())
        }

        client = BedrockClient()
        result = client.send_action(
            system_prompt="You are a DM",
            context="Character: Grog the Fighter",
            action="I attack the goblin",
        )

        assert result == "You attack the goblin."

        # Verify prompt format
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        body = json.loads(call_kwargs["body"])
        prompt = body["prompt"]

        assert "<s>[INST]" in prompt
        assert "You are a DM" in prompt
        assert "I attack the goblin" in prompt
        assert "[/INST]" in prompt

    @patch("dm.bedrock_client.boto3")
    def test_send_action_uses_reduced_max_tokens(self, mock_boto3: MagicMock) -> None:
        """Test that send_action uses 800 max tokens for cost."""
        mock_bedrock = MagicMock()
        mock_boto3.client.return_value = mock_bedrock

        response_body = json.dumps({"outputs": [{"text": "Response"}]})
        mock_bedrock.invoke_model.return_value = {
            "body": BytesIO(response_body.encode())
        }

        client = BedrockClient()
        client.send_action(
            system_prompt="You are a DM",
            context="Context",
            action="Action",
        )

        # Verify reduced max_tokens
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        body = json.loads(call_kwargs["body"])
        assert body["max_tokens"] == 800

    @patch("dm.bedrock_client.boto3")
    def test_region_configuration(self, mock_boto3: MagicMock) -> None:
        """Test that region is configurable."""
        BedrockClient(region="us-west-2")

        mock_boto3.client.assert_called_once_with(
            "bedrock-runtime", region_name="us-west-2"
        )
