"""Tests for Claude API client."""

from unittest.mock import MagicMock, patch


class TestClaudeClient:
    """Tests for ClaudeClient class."""

    def test_init_creates_anthropic_client(self) -> None:
        """Client should create Anthropic client with API key."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            from dm.claude_client import ClaudeClient

            client = ClaudeClient("test-api-key")

            mock_anthropic.assert_called_once_with(api_key="test-api-key")
            assert client.client == mock_anthropic.return_value

    def test_send_action_calls_messages_create(self) -> None:
        """send_action should call messages.create with correct parameters."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            # Mock usage response
            mock_usage = MagicMock()
            mock_usage.input_tokens = 100
            mock_usage.output_tokens = 200
            mock_usage.cache_creation_input_tokens = 0
            mock_usage.cache_read_input_tokens = 50

            mock_response = MagicMock()
            mock_response.usage = mock_usage
            mock_response.content = [MagicMock(text="DM response text")]
            mock_client.messages.create.return_value = mock_response

            from dm.claude_client import ClaudeClient

            client = ClaudeClient("test-key")
            result = client.send_action(
                system_prompt="You are a DM",
                context="Character: Thorin, HP: 10",
                action="I attack the goblin",
            )

            assert result == "DM response text"
            mock_client.messages.create.assert_called_once()

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["model"] == "claude-3-haiku-20240307"
            assert call_kwargs["max_tokens"] == 1024
            assert call_kwargs["system"][0]["type"] == "text"
            assert call_kwargs["system"][0]["text"] == "You are a DM"
            assert call_kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
            assert "[Player Action]: I attack the goblin" in call_kwargs["messages"][0]["content"]

    def test_send_action_logs_token_usage(self) -> None:
        """send_action should log token usage and cost metrics."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            mock_usage = MagicMock()
            mock_usage.input_tokens = 1000
            mock_usage.output_tokens = 500
            mock_usage.cache_creation_input_tokens = 800
            mock_usage.cache_read_input_tokens = 200

            mock_response = MagicMock()
            mock_response.usage = mock_usage
            mock_response.content = [MagicMock(text="Response")]
            mock_client.messages.create.return_value = mock_response

            from dm.claude_client import ClaudeClient

            with patch("dm.claude_client.logger") as mock_logger:
                client = ClaudeClient("test-key")
                client.send_action("system", "context", "action")

                mock_logger.info.assert_called()
                call_args = mock_logger.info.call_args
                assert call_args.args[0] == "Claude API usage"
                extra = call_args.kwargs["extra"]
                assert extra["input_tokens"] == 1000
                assert extra["output_tokens"] == 500
                assert extra["cache_creation_input_tokens"] == 800
                assert extra["cache_read_input_tokens"] == 200
                assert "estimated_cost_usd" in extra

    def test_send_action_handles_missing_cache_tokens(self) -> None:
        """send_action should handle missing cache token attributes."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            # Usage without cache attributes
            mock_usage = MagicMock(spec=["input_tokens", "output_tokens"])
            mock_usage.input_tokens = 100
            mock_usage.output_tokens = 50

            mock_response = MagicMock()
            mock_response.usage = mock_usage
            mock_response.content = [MagicMock(text="Response")]
            mock_client.messages.create.return_value = mock_response

            from dm.claude_client import ClaudeClient

            # Should not raise
            client = ClaudeClient("test-key")
            result = client.send_action("system", "context", "action")

            assert result == "Response"

    def test_model_constant(self) -> None:
        """ClaudeClient should use Haiku 3 model."""
        from dm.claude_client import ClaudeClient

        assert ClaudeClient.MODEL == "claude-3-haiku-20240307"

    def test_max_tokens_constant(self) -> None:
        """ClaudeClient should have max_tokens of 1024."""
        from dm.claude_client import ClaudeClient

        assert ClaudeClient.MAX_TOKENS == 1024
