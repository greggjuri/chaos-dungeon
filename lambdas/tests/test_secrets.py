"""Tests for SSM secrets helper."""

from unittest.mock import MagicMock, patch

import pytest


class TestGetClaudeApiKey:
    """Tests for get_claude_api_key function."""

    def test_get_api_key_success(self) -> None:
        """Test successful API key retrieval."""
        # Need to clear the lru_cache and reimport
        from shared import secrets

        secrets.get_claude_api_key.cache_clear()

        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "test-api-key-12345"}}

        with patch("boto3.client", return_value=mock_ssm):
            result = secrets.get_claude_api_key()

        assert result == "test-api-key-12345"
        mock_ssm.get_parameter.assert_called_once_with(
            Name="/automations/dev/secrets/anthropic_api_key",
            WithDecryption=True,
        )

        # Clear cache for other tests
        secrets.get_claude_api_key.cache_clear()

    def test_get_api_key_with_env_override(self) -> None:
        """Test API key retrieval with custom parameter name."""
        from shared import secrets

        secrets.get_claude_api_key.cache_clear()

        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "custom-key"}}

        with (
            patch("boto3.client", return_value=mock_ssm),
            patch.dict(
                "os.environ",
                {"CLAUDE_API_KEY_PARAM": "/custom/path/api-key"},
            ),
        ):
            result = secrets.get_claude_api_key()

        assert result == "custom-key"
        mock_ssm.get_parameter.assert_called_once_with(
            Name="/custom/path/api-key",
            WithDecryption=True,
        )

        secrets.get_claude_api_key.cache_clear()

    def test_get_api_key_cached(self) -> None:
        """Test that API key is cached."""
        from shared import secrets

        secrets.get_claude_api_key.cache_clear()

        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "cached-key"}}

        with patch("boto3.client", return_value=mock_ssm):
            result1 = secrets.get_claude_api_key()
            result2 = secrets.get_claude_api_key()

        assert result1 == "cached-key"
        assert result2 == "cached-key"
        # Should only be called once due to caching
        assert mock_ssm.get_parameter.call_count == 1

        secrets.get_claude_api_key.cache_clear()

    def test_get_api_key_ssm_error(self) -> None:
        """Test handling of SSM errors."""
        from botocore.exceptions import ClientError

        from shared import secrets

        secrets.get_claude_api_key.cache_clear()

        mock_ssm = MagicMock()
        mock_ssm.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound", "Message": "Not found"}},
            "GetParameter",
        )

        with (
            patch("boto3.client", return_value=mock_ssm),
            pytest.raises(ClientError),
        ):
            secrets.get_claude_api_key()

        secrets.get_claude_api_key.cache_clear()
