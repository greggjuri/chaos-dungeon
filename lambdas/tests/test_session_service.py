"""Tests for session service module."""

from unittest.mock import MagicMock, patch

import pytest

from session.models import CampaignSetting, SessionCreateRequest
from session.service import MAX_SESSIONS_PER_USER, SessionService
from shared.exceptions import ConflictError, NotFoundError


@pytest.fixture
def mock_db():
    """Create a mock DynamoDB client."""
    return MagicMock()


@pytest.fixture
def service(mock_db):
    """Create a SessionService with mocked DB."""
    return SessionService(mock_db)


class TestCreateSession:
    """Tests for session creation."""

    def test_create_session_success(self, service, mock_db):
        """Create session should return session data with opening message."""
        # Mock character exists
        mock_db.get_item.return_value = {
            "character_id": "char-123",
            "name": "Thorin",
        }
        # Mock no existing sessions
        mock_db.query_by_pk.return_value = []

        request = SessionCreateRequest(
            character_id="12345678-1234-4123-a123-123456789012",
            campaign_setting=CampaignSetting.DARK_FOREST,
        )

        with patch("session.service.generate_id", return_value="sess-123"):
            with patch("session.service.utc_now", return_value="2026-01-01T00:00:00Z"):
                result = service.create_session("user-123", request)

        assert result["session_id"] == "sess-123"
        assert result["character_id"] == "12345678-1234-4123-a123-123456789012"
        assert result["campaign_setting"] == "dark_forest"
        assert "Dark Forest" in result["current_location"]
        assert len(result["message_history"]) == 1
        assert result["message_history"][0]["role"] == "dm"
        assert "Thorin" in result["message_history"][0]["content"]

    def test_create_session_character_not_found(self, service, mock_db):
        """Create session should raise NotFoundError for non-existent character."""
        mock_db.get_item.return_value = None

        request = SessionCreateRequest(
            character_id="12345678-1234-4123-a123-123456789012",
        )

        with pytest.raises(NotFoundError) as exc_info:
            service.create_session("user-123", request)

        assert exc_info.value.resource_type == "Character"

    def test_create_session_limit_exceeded(self, service, mock_db):
        """Create session should raise ConflictError when limit reached."""
        mock_db.get_item.return_value = {"character_id": "char-123", "name": "Test"}
        # Mock 10 existing sessions
        mock_db.query_by_pk.return_value = [{"session_id": f"sess-{i}"} for i in range(10)]

        request = SessionCreateRequest(
            character_id="12345678-1234-4123-a123-123456789012",
        )

        with pytest.raises(ConflictError) as exc_info:
            service.create_session("user-123", request)

        assert str(MAX_SESSIONS_PER_USER) in exc_info.value.message

    def test_create_session_default_campaign(self, service, mock_db):
        """Create session with default campaign setting."""
        mock_db.get_item.return_value = {"character_id": "char-123", "name": "Hero"}
        mock_db.query_by_pk.return_value = []

        request = SessionCreateRequest(
            character_id="12345678-1234-4123-a123-123456789012",
        )

        result = service.create_session("user-123", request)

        assert result["campaign_setting"] == "default"
        assert "Rusty Tankard" in result["current_location"]

    def test_create_session_calls_db_put(self, service, mock_db):
        """Create session should call db.put_item."""
        mock_db.get_item.return_value = {"character_id": "char-123", "name": "Test"}
        mock_db.query_by_pk.return_value = []

        request = SessionCreateRequest(
            character_id="12345678-1234-4123-a123-123456789012",
        )

        with patch("session.service.generate_id", return_value="sess-456"):
            service.create_session("user-123", request)

        mock_db.put_item.assert_called_once()
        call_args = mock_db.put_item.call_args
        assert call_args.kwargs["pk"] == "USER#user-123"
        assert call_args.kwargs["sk"] == "SESS#sess-456"


class TestListSessions:
    """Tests for listing sessions."""

    def test_list_sessions_empty(self, service, mock_db):
        """List should return empty list when no sessions."""
        mock_db.query_by_pk.return_value = []

        result = service.list_sessions("user-123")

        assert result == []

    def test_list_sessions_with_character_names(self, service, mock_db):
        """List should return sessions with character names joined."""
        mock_db.query_by_pk.return_value = [
            {
                "session_id": "sess-1",
                "character_id": "char-1",
                "campaign_setting": "dark_forest",
                "current_location": "The Forest",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": None,
            }
        ]
        mock_db.get_item.return_value = {"name": "Thorin"}

        result = service.list_sessions("user-123")

        assert len(result) == 1
        assert result[0]["character_name"] == "Thorin"
        assert result[0]["session_id"] == "sess-1"

    def test_list_sessions_filter_by_character(self, service, mock_db):
        """List should filter by character_id when provided."""
        mock_db.query_by_pk.return_value = [
            {"session_id": "sess-1", "character_id": "char-1", "campaign_setting": "default",
             "current_location": "Tavern", "created_at": "2026-01-01T00:00:00Z"},
            {"session_id": "sess-2", "character_id": "char-2", "campaign_setting": "default",
             "current_location": "Forest", "created_at": "2026-01-02T00:00:00Z"},
        ]
        mock_db.get_item.return_value = {"name": "Test"}

        result = service.list_sessions("user-123", character_id="char-1")

        assert len(result) == 1
        assert result[0]["session_id"] == "sess-1"

    def test_list_sessions_deleted_character(self, service, mock_db):
        """List should show 'Deleted Character' for missing characters."""
        mock_db.query_by_pk.return_value = [
            {
                "session_id": "sess-1",
                "character_id": "deleted-char",
                "campaign_setting": "default",
                "current_location": "Unknown",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        mock_db.get_item.return_value = None  # Character deleted

        result = service.list_sessions("user-123")

        assert result[0]["character_name"] == "Deleted Character"


class TestGetSession:
    """Tests for getting a single session."""

    def test_get_session_success(self, service, mock_db):
        """Get should return full session data."""
        mock_db.get_item_or_raise.return_value = {
            "PK": "USER#user-123",
            "SK": "SESS#sess-1",
            "session_id": "sess-1",
            "character_id": "char-1",
            "campaign_setting": "dark_forest",
            "message_history": [],
        }

        result = service.get_session("user-123", "sess-1")

        assert result["session_id"] == "sess-1"
        assert "PK" not in result
        assert "SK" not in result

    def test_get_session_not_found(self, service, mock_db):
        """Get should raise NotFoundError for missing session."""
        mock_db.get_item_or_raise.side_effect = NotFoundError("Session", "sess-999")

        with pytest.raises(NotFoundError):
            service.get_session("user-123", "sess-999")


class TestGetMessageHistory:
    """Tests for message history pagination."""

    def test_get_history_empty(self, service, mock_db):
        """Get history should return empty list for session with no messages."""
        mock_db.get_item_or_raise.return_value = {
            "session_id": "sess-1",
            "message_history": [],
        }

        result = service.get_message_history("user-123", "sess-1")

        assert result["messages"] == []
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    def test_get_history_returns_newest_first(self, service, mock_db):
        """Get history should return messages in reverse chronological order."""
        mock_db.get_item_or_raise.return_value = {
            "session_id": "sess-1",
            "message_history": [
                {"role": "dm", "content": "First", "timestamp": "2026-01-01T00:00:00Z"},
                {"role": "player", "content": "Second", "timestamp": "2026-01-01T00:01:00Z"},
                {"role": "dm", "content": "Third", "timestamp": "2026-01-01T00:02:00Z"},
            ],
        }

        result = service.get_message_history("user-123", "sess-1")

        assert result["messages"][0]["content"] == "Third"
        assert result["messages"][1]["content"] == "Second"
        assert result["messages"][2]["content"] == "First"

    def test_get_history_pagination(self, service, mock_db):
        """Get history should support pagination with limit and cursor."""
        messages = [
            {"role": "dm", "content": f"Message {i}", "timestamp": f"2026-01-01T00:{i:02d}:00Z"}
            for i in range(25)
        ]
        mock_db.get_item_or_raise.return_value = {
            "session_id": "sess-1",
            "message_history": messages,
        }

        result = service.get_message_history("user-123", "sess-1", limit=10)

        assert len(result["messages"]) == 10
        assert result["has_more"] is True
        assert result["next_cursor"] is not None

    def test_get_history_with_before_cursor(self, service, mock_db):
        """Get history should filter messages before cursor timestamp."""
        mock_db.get_item_or_raise.return_value = {
            "session_id": "sess-1",
            "message_history": [
                {"role": "dm", "content": "Old", "timestamp": "2026-01-01T00:00:00Z"},
                {"role": "dm", "content": "New", "timestamp": "2026-01-01T00:10:00Z"},
            ],
        }

        result = service.get_message_history(
            "user-123", "sess-1", before="2026-01-01T00:05:00Z"
        )

        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Old"


class TestDeleteSession:
    """Tests for deleting a session."""

    def test_delete_session_success(self, service, mock_db):
        """Delete should call db.delete_item."""
        mock_db.get_item_or_raise.return_value = {
            "session_id": "sess-1",
        }

        service.delete_session("user-123", "sess-1")

        mock_db.delete_item.assert_called_once_with(
            pk="USER#user-123",
            sk="SESS#sess-1",
        )

    def test_delete_session_not_found(self, service, mock_db):
        """Delete should raise NotFoundError for missing session."""
        mock_db.get_item_or_raise.side_effect = NotFoundError("Session", "sess-999")

        with pytest.raises(NotFoundError):
            service.delete_session("user-123", "sess-999")

        mock_db.delete_item.assert_not_called()
