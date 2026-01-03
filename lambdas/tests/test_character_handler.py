"""Integration tests for character Lambda handler."""

import json
from unittest.mock import MagicMock

import pytest
from moto import mock_aws

from character.handler import lambda_handler, reset_service


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
        "queryStringParameters": None,
        "body": json.dumps(body) if body else None,
        "requestContext": {
            "stage": "dev",
            "requestId": "test-request-id",
        },
        "resource": path,
    }
    return event


class TestCreateCharacter:
    """Tests for POST /characters."""

    @mock_aws
    def test_create_returns_201(self, dynamodb_table):
        """POST /characters should return 201 with character data."""
        event = make_event(
            "POST",
            "/characters",
            body={"name": "Thorin", "character_class": "fighter"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["name"] == "Thorin"
        assert body["character_class"] == "fighter"
        assert body["level"] == 1
        assert "character_id" in body
        assert "stats" in body
        assert "hp" in body

    @mock_aws
    def test_create_invalid_class_returns_400(self, dynamodb_table):
        """POST /characters with invalid class should return 400."""
        event = make_event(
            "POST",
            "/characters",
            body={"name": "Test", "character_class": "invalid"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 400

    @mock_aws
    def test_create_missing_name_returns_400(self, dynamodb_table):
        """POST /characters without name should return 400."""
        event = make_event(
            "POST",
            "/characters",
            body={"character_class": "fighter"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 400

    @mock_aws
    def test_create_short_name_returns_400(self, dynamodb_table):
        """POST /characters with short name should return 400."""
        event = make_event(
            "POST",
            "/characters",
            body={"name": "AB", "character_class": "fighter"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 400

    @mock_aws
    def test_create_special_chars_in_name_returns_400(self, dynamodb_table):
        """POST /characters with special chars in name should return 400."""
        event = make_event(
            "POST",
            "/characters",
            body={"name": "Test@#$", "character_class": "fighter"},
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 400

    def test_create_missing_user_id_returns_401(self):
        """POST /characters without X-User-Id should return 401."""
        event = make_event(
            "POST",
            "/characters",
            body={"name": "Test", "character_class": "fighter"},
            user_id=None,
        )

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 401


class TestListCharacters:
    """Tests for GET /characters."""

    @mock_aws
    def test_list_empty_returns_200(self, dynamodb_table):
        """GET /characters should return 200 with empty list."""
        event = make_event("GET", "/characters")

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body == {"characters": []}

    @mock_aws
    def test_list_returns_summaries(self, dynamodb_table):
        """GET /characters should return character summaries."""
        # Create a character first
        create_event = make_event(
            "POST",
            "/characters",
            body={"name": "Thorin", "character_class": "fighter"},
        )
        lambda_handler(create_event, MagicMock())

        # List characters
        event = make_event("GET", "/characters")
        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["characters"]) == 1
        assert body["characters"][0]["name"] == "Thorin"
        # Summaries should not include stats, hp, etc.
        assert "stats" not in body["characters"][0]
        assert "hp" not in body["characters"][0]

    def test_list_missing_user_id_returns_401(self):
        """GET /characters without X-User-Id should return 401."""
        event = make_event("GET", "/characters", user_id=None)

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 401


class TestGetCharacter:
    """Tests for GET /characters/{characterId}."""

    @mock_aws
    def test_get_returns_200(self, dynamodb_table):
        """GET /characters/{id} should return 200 with full character."""
        # Create a character first
        create_event = make_event(
            "POST",
            "/characters",
            body={"name": "Thorin", "character_class": "fighter"},
        )
        create_response = lambda_handler(create_event, MagicMock())
        character_id = json.loads(create_response["body"])["character_id"]

        # Get the character
        event = make_event(
            "GET",
            f"/characters/{character_id}",
            path_params={"characterId": character_id},
        )
        # Fix resource to match path parameter pattern
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["character_id"] == character_id
        assert body["name"] == "Thorin"
        assert "stats" in body
        assert "hp" in body

    @mock_aws
    def test_get_not_found_returns_404(self, dynamodb_table):
        """GET /characters/{id} for non-existent should return 404."""
        event = make_event(
            "GET",
            "/characters/nonexistent-id",
            path_params={"characterId": "nonexistent-id"},
        )
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 404

    def test_get_missing_user_id_returns_401(self):
        """GET /characters/{id} without X-User-Id should return 401."""
        event = make_event(
            "GET",
            "/characters/some-id",
            user_id=None,
            path_params={"characterId": "some-id"},
        )
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 401


class TestUpdateCharacter:
    """Tests for PATCH /characters/{characterId}."""

    @mock_aws
    def test_update_returns_200(self, dynamodb_table):
        """PATCH /characters/{id} should return 200 with updated character."""
        # Create a character first
        create_event = make_event(
            "POST",
            "/characters",
            body={"name": "Thorin", "character_class": "fighter"},
        )
        create_response = lambda_handler(create_event, MagicMock())
        character_id = json.loads(create_response["body"])["character_id"]

        # Update the character
        event = make_event(
            "PATCH",
            f"/characters/{character_id}",
            body={"name": "Thorin the Brave"},
            path_params={"characterId": character_id},
        )
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["name"] == "Thorin the Brave"

    @mock_aws
    def test_update_not_found_returns_404(self, dynamodb_table):
        """PATCH /characters/{id} for non-existent should return 404."""
        event = make_event(
            "PATCH",
            "/characters/nonexistent-id",
            body={"name": "New Name"},
            path_params={"characterId": "nonexistent-id"},
        )
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 404

    @mock_aws
    def test_update_invalid_name_returns_400(self, dynamodb_table):
        """PATCH /characters/{id} with invalid name should return 400."""
        # Create a character first
        create_event = make_event(
            "POST",
            "/characters",
            body={"name": "Thorin", "character_class": "fighter"},
        )
        create_response = lambda_handler(create_event, MagicMock())
        character_id = json.loads(create_response["body"])["character_id"]

        # Update with invalid name
        event = make_event(
            "PATCH",
            f"/characters/{character_id}",
            body={"name": "A"},  # Too short
            path_params={"characterId": character_id},
        )
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 400


class TestDeleteCharacter:
    """Tests for DELETE /characters/{characterId}."""

    @mock_aws
    def test_delete_returns_204(self, dynamodb_table):
        """DELETE /characters/{id} should return 204."""
        # Create a character first
        create_event = make_event(
            "POST",
            "/characters",
            body={"name": "Thorin", "character_class": "fighter"},
        )
        create_response = lambda_handler(create_event, MagicMock())
        character_id = json.loads(create_response["body"])["character_id"]

        # Delete the character
        event = make_event(
            "DELETE",
            f"/characters/{character_id}",
            path_params={"characterId": character_id},
        )
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 204

    @mock_aws
    def test_delete_not_found_returns_404(self, dynamodb_table):
        """DELETE /characters/{id} for non-existent should return 404."""
        event = make_event(
            "DELETE",
            "/characters/nonexistent-id",
            path_params={"characterId": "nonexistent-id"},
        )
        event["resource"] = "/characters/{characterId}"

        response = lambda_handler(event, MagicMock())

        assert response["statusCode"] == 404

    @mock_aws
    def test_delete_removes_character(self, dynamodb_table):
        """DELETE /characters/{id} should remove character from list."""
        # Create a character
        create_event = make_event(
            "POST",
            "/characters",
            body={"name": "Thorin", "character_class": "fighter"},
        )
        create_response = lambda_handler(create_event, MagicMock())
        character_id = json.loads(create_response["body"])["character_id"]

        # Delete it
        delete_event = make_event(
            "DELETE",
            f"/characters/{character_id}",
            path_params={"characterId": character_id},
        )
        delete_event["resource"] = "/characters/{characterId}"
        lambda_handler(delete_event, MagicMock())

        # Verify it's gone
        list_event = make_event("GET", "/characters")
        list_response = lambda_handler(list_event, MagicMock())
        body = json.loads(list_response["body"])

        assert len(body["characters"]) == 0
