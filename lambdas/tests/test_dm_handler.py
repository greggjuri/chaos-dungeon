"""Tests for DM handler module."""

import json
from unittest.mock import MagicMock, patch

import anthropic
import pytest

from dm.models import ActionResponse, CharacterSnapshot, DiceRoll, Enemy, StateChanges


@pytest.fixture
def mock_service():
    """Create a mock DM service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_context():
    """Create a mock Lambda context."""
    return MagicMock()


@pytest.fixture
def sample_action_response():
    """Create a sample ActionResponse."""
    return ActionResponse(
        narrative="You swing your sword at the goblin!",
        state_changes=StateChanges(hp_delta=-2, xp_delta=10),
        dice_rolls=[
            DiceRoll(type="attack", roll=15, modifier=3, total=18, success=True)
        ],
        combat_active=True,
        enemies=[Enemy(name="Goblin", hp=3, ac=12)],
        character=CharacterSnapshot(
            hp=6,
            max_hp=8,
            xp=10,
            gold=100,
            level=1,
            inventory=["Sword", "Shield"],
        ),
        character_dead=False,
        session_ended=False,
    )


def make_api_event(
    method: str = "POST",
    path: str = "/sessions/sess-123/action",
    body: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """Create a mock API Gateway event."""
    default_headers = {
        "Content-Type": "application/json",
        "X-User-ID": "user-123",
    }
    if headers:
        default_headers.update(headers)

    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": {"session_id": "sess-123"} if "sess-123" in path else {},
        "headers": default_headers,
        "body": json.dumps(body) if body else None,
        "requestContext": {
            "requestId": "test-request-id",
            "stage": "dev",
        },
    }


class TestPostAction:
    """Tests for POST /sessions/{session_id}/action endpoint."""

    def test_post_action_success(self, mock_service, mock_context, sample_action_response):
        """POST action should return 200 with ActionResponse."""
        mock_service.process_action.return_value = sample_action_response

        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "I attack the goblin"})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["narrative"] == "You swing your sword at the goblin!"
        assert body["character"]["hp"] == 6
        assert body["combat_active"] is True

    def test_post_action_unauthorized(self, mock_context):
        """POST action without X-User-ID should return 401."""
        # Clear any cached service
        with patch("dm.handler._service", None):
            from dm.handler import lambda_handler

            event = make_api_event(
                body={"action": "I attack"},
                headers={"X-User-ID": None},
            )
            # Remove the header completely
            del event["headers"]["X-User-ID"]

            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 401

    def test_post_action_empty_action(self, mock_service, mock_context):
        """POST action with empty action should return 400."""
        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": ""})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 400

    def test_post_action_missing_action(self, mock_service, mock_context):
        """POST action without action field should return 400."""
        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 400

    def test_post_action_action_too_long(self, mock_service, mock_context):
        """POST action with action > 500 chars should return 400."""
        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "x" * 501})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 400

    def test_post_action_session_not_found(self, mock_service, mock_context):
        """POST action for nonexistent session should return 404."""
        from shared.exceptions import NotFoundError

        mock_service.process_action.side_effect = NotFoundError("session", "sess-123")

        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "I attack"})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 404

    def test_post_action_character_not_found(self, mock_service, mock_context):
        """POST action when character is deleted should return 404."""
        from shared.exceptions import NotFoundError

        mock_service.process_action.side_effect = NotFoundError("character", "char-123")

        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "I attack"})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 404

    def test_post_action_session_ended(self, mock_service, mock_context):
        """POST action for ended session should return 400."""
        from shared.exceptions import GameStateError

        mock_service.process_action.side_effect = GameStateError(
            "Session has ended", current_state="character_death"
        )

        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "I attack"})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 400

    def test_post_action_rate_limit_error(self, mock_service, mock_context):
        """POST action hitting rate limit should return 429."""
        mock_service.process_action.side_effect = anthropic.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Rate limit exceeded"}},
        )

        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "I attack"})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 429
        body = json.loads(result["body"])
        assert "rate limit" in body["error"].lower()

    def test_post_action_connection_error(self, mock_service, mock_context):
        """POST action with connection error should return 503."""
        mock_request = MagicMock()
        mock_service.process_action.side_effect = anthropic.APIConnectionError(
            message="Connection failed",
            request=mock_request,
        )

        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "I attack"})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 503
        body = json.loads(result["body"])
        assert "unavailable" in body["error"].lower()

    def test_post_action_api_status_error(self, mock_service, mock_context):
        """POST action with API error should return 500."""
        mock_service.process_action.side_effect = anthropic.APIStatusError(
            message="API Error",
            response=MagicMock(status_code=500),
            body={"error": {"message": "Internal error"}},
        )

        with patch("dm.handler._service", mock_service):
            from dm.handler import lambda_handler

            event = make_api_event(body={"action": "I attack"})
            result = lambda_handler(event, mock_context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "DM unavailable" in body["error"]


class TestGetService:
    """Tests for service singleton."""

    def test_get_service_creates_singleton(self):
        """get_service should create and cache service instance."""
        import dm.handler

        # Reset cached service
        dm.handler._service = None

        with patch("dm.handler.DynamoDBClient") as mock_db_class:
            with patch("dm.handler.config") as mock_config:
                mock_config.table_name = "test-table"

                service1 = dm.handler.get_service()
                service2 = dm.handler.get_service()

                mock_db_class.assert_called_once()
                assert service1 is service2

        # Clean up
        dm.handler._service = None


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_allows_required_headers(self):
        """CORS should allow Content-Type and X-User-ID headers."""
        from dm.handler import cors_config

        assert "Content-Type" in cors_config.allow_headers
        assert "X-User-ID" in cors_config.allow_headers or "X-User-Id" in cors_config.allow_headers

    def test_cors_config_default_origin_in_dev(self):
        """CORS should allow all origins in dev."""
        from dm.handler import cors_config

        # In test environment, config.is_production is False
        # CORSConfig stores origins as _allowed_origins
        assert "*" in cors_config._allowed_origins
