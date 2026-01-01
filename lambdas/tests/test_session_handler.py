"""Integration tests for session Lambda handler."""

import json
from unittest.mock import MagicMock

import pytest
from moto import mock_aws

from session.handler import lambda_handler, reset_service


@pytest.fixture(autouse=True)
def reset_handler():
    """Reset handler state before each test."""
    reset_service()
    yield
    reset_service()


def make_event(
    method: str,
    path: str,
    body: dict | None = None,
    user_id: str | None = "test-user-123",
    path_params: dict | None = None,
    query_params: dict | None = None,
) -> dict:
    """Create an API Gateway event for testing."""
    headers = {"Content-Type": "application/json"}
    if user_id:
        headers["X-User-Id"] = user_id

    event = {
        "httpMethod": method,
        "path": path,
        "headers": headers,
        "pathParameters": path_params or {},
        "queryStringParameters": query_params,
        "body": json.dumps(body) if body else None,
        "requestContext": {
            "stage": "dev",
            "requestId": "test-request-id",
        },
        "resource": path,
    }
    return event


def create_character(user_id: str = "test-user-123") -> str:
    """Helper to create a character and return its ID."""
    from character.handler import lambda_handler as char_handler
    from character.handler import reset_service as reset_char

    reset_char()
    event = {
        "httpMethod": "POST",
        "path": "/characters",
        "headers": {"Content-Type": "application/json", "X-User-Id": user_id},
        "pathParameters": {},
        "queryStringParameters": None,
        "body": json.dumps({"name": "TestHero", "character_class": "fighter"}),
        "requestContext": {"stage": "dev", "requestId": "test"},
        "resource": "/characters",
    }
    response = char_handler(event, MagicMock())
    reset_char()
    return json.loads(response["body"])["character_id"]


class TestCreateSession:
    """Tests for POST /sessions."""

    @mock_aws
    def test_create_returns_201(self, dynamodb_table):
        """POST /sessions should return 201 with session data."""
        character_id = create_character()

        event = make_event(
            "POST",
            "/sessions",
            body={"character_id": character_id, "campaign_setting": "dark_forest"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["character_id"] == character_id
        assert body["campaign_setting"] == "dark_forest"
        assert "session_id" in body
        assert "message_history" in body
        assert len(body["message_history"]) == 1

    @mock_aws
    def test_create_invalid_campaign_returns_400(self, dynamodb_table):
        """POST /sessions with invalid campaign should return 400."""
        character_id = create_character()

        event = make_event(
            "POST",
            "/sessions",
            body={"character_id": character_id, "campaign_setting": "invalid"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 400

    @mock_aws
    def test_create_invalid_character_id_returns_400(self, dynamodb_table):
        """POST /sessions with invalid UUID should return 400."""
        event = make_event(
            "POST",
            "/sessions",
            body={"character_id": "not-a-uuid", "campaign_setting": "default"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 400

    def test_create_missing_user_id_returns_401(self):
        """POST /sessions without X-User-Id should return 401."""
        event = make_event(
            "POST",
            "/sessions",
            body={"character_id": "12345678-1234-4123-a123-123456789012"},
            user_id=None,
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 401

    @mock_aws
    def test_create_nonexistent_character_returns_404(self, dynamodb_table):
        """POST /sessions with non-existent character should return 404."""
        event = make_event(
            "POST",
            "/sessions",
            body={"character_id": "12345678-1234-4123-a123-123456789012"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 404

    @mock_aws
    def test_create_session_limit_returns_409(self, dynamodb_table):
        """POST /sessions when limit reached should return 409."""
        character_id = create_character()

        # Create 10 sessions
        for _ in range(10):
            event = make_event(
                "POST",
                "/sessions",
                body={"character_id": character_id},
            )
            lambda_handler(event, MagicMock())

        # 11th should fail
        event = make_event(
            "POST",
            "/sessions",
            body={"character_id": character_id},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 409


class TestListSessions:
    """Tests for GET /sessions."""

    @mock_aws
    def test_list_empty_returns_200(self, dynamodb_table):
        """GET /sessions should return 200 with empty list."""
        event = make_event("GET", "/sessions")

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body == {"sessions": []}

    @mock_aws
    def test_list_returns_sessions_with_names(self, dynamodb_table):
        """GET /sessions should return sessions with character names."""
        character_id = create_character()

        # Create a session
        create_event = make_event(
            "POST",
            "/sessions",
            body={"character_id": character_id},
        )
        lambda_handler(create_event, MagicMock())

        # List sessions
        event = make_event("GET", "/sessions")
        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["sessions"]) == 1
        assert body["sessions"][0]["character_name"] == "TestHero"

    @mock_aws
    def test_list_filter_by_character(self, dynamodb_table):
        """GET /sessions should filter by character_id."""
        char1 = create_character()
        char2 = create_character()

        # Create sessions for both characters
        lambda_handler(
            make_event("POST", "/sessions", body={"character_id": char1}),
            MagicMock(),
        )
        lambda_handler(
            make_event("POST", "/sessions", body={"character_id": char2}),
            MagicMock(),
        )

        # Filter by char1
        event = make_event(
            "GET",
            "/sessions",
            query_params={"character_id": char1},
        )
        response = lambda_handler(event, MagicMock())

        body = json.loads(response["body"])
        assert len(body["sessions"]) == 1
        assert body["sessions"][0]["character_id"] == char1

    def test_list_missing_user_id_returns_401(self):
        """GET /sessions without X-User-Id should return 401."""
        event = make_event("GET", "/sessions", user_id=None)

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 401


class TestGetSession:
    """Tests for GET /sessions/{sessionId}."""

    @mock_aws
    def test_get_returns_200(self, dynamodb_table):
        """GET /sessions/{id} should return 200 with full session."""
        character_id = create_character()

        # Create session
        create_response = lambda_handler(
            make_event("POST", "/sessions", body={"character_id": character_id}),
            MagicMock(),
        )
        session_id = json.loads(create_response["body"])["session_id"]

        # Get session
        event = make_event(
            "GET",
            f"/sessions/{session_id}",
            path_params={"sessionId": session_id},
        )
        event["resource"] = "/sessions/{sessionId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["session_id"] == session_id
        assert "message_history" in body
        assert "world_state" in body

    @mock_aws
    def test_get_not_found_returns_404(self, dynamodb_table):
        """GET /sessions/{id} for non-existent should return 404."""
        event = make_event(
            "GET",
            "/sessions/nonexistent-id",
            path_params={"sessionId": "nonexistent-id"},
        )
        event["resource"] = "/sessions/{sessionId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 404


class TestGetMessageHistory:
    """Tests for GET /sessions/{sessionId}/history."""

    @mock_aws
    def test_get_history_returns_200(self, dynamodb_table):
        """GET /sessions/{id}/history should return paginated messages."""
        character_id = create_character()

        # Create session
        create_response = lambda_handler(
            make_event("POST", "/sessions", body={"character_id": character_id}),
            MagicMock(),
        )
        session_id = json.loads(create_response["body"])["session_id"]

        # Get history
        event = make_event(
            "GET",
            f"/sessions/{session_id}/history",
            path_params={"sessionId": session_id},
        )
        event["resource"] = "/sessions/{sessionId}/history"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "messages" in body
        assert "has_more" in body
        assert "next_cursor" in body

    @mock_aws
    def test_get_history_not_found_returns_404(self, dynamodb_table):
        """GET /sessions/{id}/history for non-existent should return 404."""
        event = make_event(
            "GET",
            "/sessions/nonexistent-id/history",
            path_params={"sessionId": "nonexistent-id"},
        )
        event["resource"] = "/sessions/{sessionId}/history"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 404


class TestDeleteSession:
    """Tests for DELETE /sessions/{sessionId}."""

    @mock_aws
    def test_delete_returns_204(self, dynamodb_table):
        """DELETE /sessions/{id} should return 204."""
        character_id = create_character()

        # Create session
        create_response = lambda_handler(
            make_event("POST", "/sessions", body={"character_id": character_id}),
            MagicMock(),
        )
        session_id = json.loads(create_response["body"])["session_id"]

        # Delete session
        event = make_event(
            "DELETE",
            f"/sessions/{session_id}",
            path_params={"sessionId": session_id},
        )
        event["resource"] = "/sessions/{sessionId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 204

    @mock_aws
    def test_delete_not_found_returns_404(self, dynamodb_table):
        """DELETE /sessions/{id} for non-existent should return 404."""
        event = make_event(
            "DELETE",
            "/sessions/nonexistent-id",
            path_params={"sessionId": "nonexistent-id"},
        )
        event["resource"] = "/sessions/{sessionId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 404

    @mock_aws
    def test_delete_removes_session(self, dynamodb_table):
        """DELETE /sessions/{id} should remove session from list."""
        character_id = create_character()

        # Create session
        create_response = lambda_handler(
            make_event("POST", "/sessions", body={"character_id": character_id}),
            MagicMock(),
        )
        session_id = json.loads(create_response["body"])["session_id"]

        # Delete it
        delete_event = make_event(
            "DELETE",
            f"/sessions/{session_id}",
            path_params={"sessionId": session_id},
        )
        delete_event["resource"] = "/sessions/{sessionId}"
        lambda_handler(delete_event, MagicMock())

        # Verify it's gone
        list_event = make_event("GET", "/sessions")
        list_response = lambda_handler(list_event, MagicMock())
        body = json.loads(list_response["body"])

        assert len(body["sessions"]) == 0
