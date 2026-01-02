"""Tests for DM service module."""

from unittest.mock import MagicMock, patch

import pytest

from dm.models import DMResponse, Enemy, StateChanges
from dm.service import MAX_MESSAGE_HISTORY, DMService
from shared.exceptions import GameStateError, NotFoundError


@pytest.fixture
def mock_db():
    """Create a mock DynamoDB client."""
    return MagicMock()


@pytest.fixture
def mock_claude_client():
    """Create a mock Claude client."""
    client = MagicMock()
    client.send_action.return_value = """You swing your sword at the goblin, hitting it squarely!

```json
{
    "state_changes": {
        "hp_delta": -2,
        "xp_delta": 10,
        "gold_delta": 0
    },
    "dice_rolls": [
        {
            "type": "attack",
            "roll": 15,
            "modifier": 3,
            "total": 18,
            "success": true
        }
    ],
    "combat_active": true,
    "enemies": [
        {
            "name": "Goblin",
            "hp": 3,
            "ac": 12,
            "max_hp": 6
        }
    ]
}
```"""
    return client


@pytest.fixture
def service(mock_db, mock_claude_client):
    """Create a DMService with mocked dependencies."""
    return DMService(mock_db, mock_claude_client)


@pytest.fixture
def sample_session():
    """Create a sample session dict."""
    return {
        "session_id": "sess-123",
        "user_id": "user-123",
        "character_id": "char-123",
        "campaign_setting": "default",
        "current_location": "Tavern",
        "status": "active",
        "world_state": {"met_bartender": True},
        "message_history": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_character():
    """Create a sample character dict."""
    return {
        "character_id": "char-123",
        "user_id": "user-123",
        "name": "Thorin",
        "character_class": "fighter",
        "level": 1,
        "xp": 0,
        "hp": 8,
        "max_hp": 8,
        "gold": 100,
        "stats": {
            "strength": 16,
            "intelligence": 10,
            "wisdom": 12,
            "dexterity": 13,
            "constitution": 15,
            "charisma": 11,
        },
        "inventory": [
            {"name": "Sword", "quantity": 1, "weight": 3.0},
            {"name": "Shield", "quantity": 1, "weight": 6.0},
        ],
    }


class TestApplyStateChanges:
    """Tests for _apply_state_changes method."""

    def test_hp_delta_positive(self, service, sample_character, sample_session):
        """HP should increase with positive delta."""
        sample_character["hp"] = 5
        dm_response = DMResponse(
            narrative="Healed!",
            state_changes=StateChanges(hp_delta=3),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["hp"] == 8

    def test_hp_delta_negative(self, service, sample_character, sample_session):
        """HP should decrease with negative delta."""
        dm_response = DMResponse(
            narrative="Ouch!",
            state_changes=StateChanges(hp_delta=-3),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["hp"] == 5

    def test_hp_cannot_exceed_max(self, service, sample_character, sample_session):
        """HP should not exceed max_hp."""
        dm_response = DMResponse(
            narrative="Full heal!",
            state_changes=StateChanges(hp_delta=100),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["hp"] == sample_character["max_hp"]

    def test_hp_cannot_go_below_zero(self, service, sample_character, sample_session):
        """HP should not go below 0."""
        dm_response = DMResponse(
            narrative="Critical hit!",
            state_changes=StateChanges(hp_delta=-100),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["hp"] == 0

    def test_gold_delta_positive(self, service, sample_character, sample_session):
        """Gold should increase with positive delta."""
        dm_response = DMResponse(
            narrative="Loot!",
            state_changes=StateChanges(gold_delta=50),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["gold"] == 150

    def test_gold_delta_negative(self, service, sample_character, sample_session):
        """Gold should decrease with negative delta."""
        dm_response = DMResponse(
            narrative="Paid",
            state_changes=StateChanges(gold_delta=-30),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["gold"] == 70

    def test_gold_cannot_go_negative(self, service, sample_character, sample_session):
        """Gold should not go below 0."""
        dm_response = DMResponse(
            narrative="Robbed!",
            state_changes=StateChanges(gold_delta=-1000),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["gold"] == 0

    def test_xp_delta(self, service, sample_character, sample_session):
        """XP should accumulate."""
        dm_response = DMResponse(
            narrative="Victory!",
            state_changes=StateChanges(xp_delta=100),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert char["xp"] == 100

    def test_inventory_add(self, service, sample_character, sample_session):
        """Items should be added to inventory."""
        dm_response = DMResponse(
            narrative="Found!",
            state_changes=StateChanges(inventory_add=["Potion", "Key"]),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        inventory_names = [item["name"] for item in char["inventory"]]
        assert "Potion" in inventory_names
        assert "Key" in inventory_names

    def test_inventory_add_no_duplicates(self, service, sample_character, sample_session):
        """Duplicate items should not be added."""
        dm_response = DMResponse(
            narrative="Found!",
            state_changes=StateChanges(inventory_add=["Sword"]),  # Already has Sword
        )

        original_count = len(sample_character["inventory"])
        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert len(char["inventory"]) == original_count

    def test_inventory_remove(self, service, sample_character, sample_session):
        """Items should be removed from inventory."""
        dm_response = DMResponse(
            narrative="Used!",
            state_changes=StateChanges(inventory_remove=["Shield"]),
        )

        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        inventory_names = [item["name"] for item in char["inventory"]]
        assert "Shield" not in inventory_names
        assert "Sword" in inventory_names

    def test_inventory_remove_nonexistent(self, service, sample_character, sample_session):
        """Removing nonexistent items should not raise error."""
        dm_response = DMResponse(
            narrative="Lost!",
            state_changes=StateChanges(inventory_remove=["NonexistentItem"]),
        )

        # Should not raise
        char, _ = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert len(char["inventory"]) == 2  # Unchanged

    def test_location_update(self, service, sample_character, sample_session):
        """Location should be updated."""
        dm_response = DMResponse(
            narrative="Entered forest",
            state_changes=StateChanges(location="Dark Forest"),
        )

        _, session = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert session["current_location"] == "Dark Forest"

    def test_location_not_updated_when_none(self, service, sample_character, sample_session):
        """Location should not change when not specified."""
        dm_response = DMResponse(
            narrative="Stayed",
            state_changes=StateChanges(),
        )

        _, session = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert session["current_location"] == "Tavern"

    def test_world_state_merge(self, service, sample_character, sample_session):
        """World state should be merged."""
        dm_response = DMResponse(
            narrative="Found secret",
            state_changes=StateChanges(world_state={"found_treasure": True}),
        )

        _, session = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert session["world_state"]["met_bartender"] is True
        assert session["world_state"]["found_treasure"] is True

    def test_combat_active_set(self, service, sample_character, sample_session):
        """Combat active state should be set."""
        dm_response = DMResponse(
            narrative="Battle!",
            combat_active=True,
            enemies=[Enemy(name="Goblin", hp=5, ac=12)],
        )

        _, session = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert session["combat_active"] is True
        assert len(session["enemies"]) == 1
        assert session["enemies"][0]["name"] == "Goblin"

    def test_combat_ended_clears_enemies(self, service, sample_character, sample_session):
        """Ending combat should clear enemies."""
        sample_session["enemies"] = [{"name": "Goblin", "hp": 0, "ac": 12}]

        dm_response = DMResponse(
            narrative="Victory!",
            combat_active=False,
        )

        _, session = service._apply_state_changes(
            sample_character, sample_session, dm_response
        )

        assert session["combat_active"] is False
        assert session["enemies"] == []


class TestAppendMessages:
    """Tests for _append_messages method."""

    def test_append_messages_adds_player_and_dm(self, service, sample_session):
        """Should append player and DM messages."""
        with patch("dm.service.datetime") as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "2026-01-01T12:00:00Z"

            session = service._append_messages(
                sample_session, "I attack", "You swing your sword!"
            )

        assert len(session["message_history"]) == 2
        assert session["message_history"][0]["role"] == "player"
        assert session["message_history"][0]["content"] == "I attack"
        assert session["message_history"][1]["role"] == "dm"
        assert session["message_history"][1]["content"] == "You swing your sword!"

    def test_append_messages_trims_to_max(self, service, sample_session):
        """Should trim messages to MAX_MESSAGE_HISTORY."""
        # Pre-fill with messages
        sample_session["message_history"] = [
            {"role": "player", "content": f"action {i}", "timestamp": "2026-01-01T00:00:00Z"}
            for i in range(MAX_MESSAGE_HISTORY - 1)
        ]

        session = service._append_messages(sample_session, "new action", "new response")

        assert len(session["message_history"]) == MAX_MESSAGE_HISTORY

    def test_append_messages_keeps_recent(self, service, sample_session):
        """Should keep most recent messages when trimming."""
        sample_session["message_history"] = [
            {"role": "player", "content": f"old action {i}", "timestamp": "2026-01-01T00:00:00Z"}
            for i in range(MAX_MESSAGE_HISTORY)
        ]

        session = service._append_messages(sample_session, "newest action", "newest response")

        # New messages should be at the end
        assert session["message_history"][-1]["content"] == "newest response"
        assert session["message_history"][-2]["content"] == "newest action"


class TestProcessAction:
    """Tests for process_action method."""

    def test_process_action_success(
        self, service, mock_db, sample_session, sample_character
    ):
        """process_action should return ActionResponse on success."""
        mock_db.get_item.side_effect = [sample_session, sample_character]

        result = service.process_action(
            session_id="sess-123",
            user_id="user-123",
            action="I attack the goblin",
        )

        assert result.narrative is not None
        assert result.character.hp >= 0
        assert mock_db.put_item.call_count == 2  # Session and character saved

    def test_process_action_session_not_found(self, service, mock_db):
        """process_action should raise NotFoundError for missing session."""
        mock_db.get_item.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            service.process_action(
                session_id="nonexistent",
                user_id="user-123",
                action="I attack",
            )

        assert exc_info.value.resource_type == "session"

    def test_process_action_character_not_found(
        self, service, mock_db, sample_session
    ):
        """process_action should raise NotFoundError for missing character."""
        mock_db.get_item.side_effect = [sample_session, None]

        with pytest.raises(NotFoundError) as exc_info:
            service.process_action(
                session_id="sess-123",
                user_id="user-123",
                action="I attack",
            )

        assert exc_info.value.resource_type == "character"

    def test_process_action_session_ended(self, service, mock_db, sample_session):
        """process_action should raise GameStateError for ended session."""
        sample_session["status"] = "ended"
        sample_session["ended_reason"] = "character_death"
        mock_db.get_item.return_value = sample_session

        with pytest.raises(GameStateError) as exc_info:
            service.process_action(
                session_id="sess-123",
                user_id="user-123",
                action="I attack",
            )

        assert "Session has ended" in str(exc_info.value)

    def test_process_action_character_death(
        self, service, mock_db, mock_claude_client, sample_session, sample_character
    ):
        """process_action should end session on character death (HP=0)."""
        sample_character["hp"] = 1
        mock_db.get_item.side_effect = [sample_session, sample_character]

        # Mock response that deals 10 damage (more than 1 HP)
        # Use the proper JSON format that the parser expects
        mock_claude_client.send_action.return_value = """The dragon breathes fire, engulfing you in a torrent of flames!

```json
{
    "state_changes": {
        "hp_delta": -10
    }
}
```"""

        result = service.process_action(
            session_id="sess-123",
            user_id="user-123",
            action="I attack the dragon",
        )

        assert result.character_dead is True
        assert result.session_ended is True
        assert result.character.hp == 0

    def test_process_action_saves_updates(
        self, service, mock_db, sample_session, sample_character
    ):
        """process_action should save character and session updates."""
        mock_db.get_item.side_effect = [sample_session, sample_character]

        service.process_action(
            session_id="sess-123",
            user_id="user-123",
            action="I attack",
        )

        # Verify put_item was called for both
        assert mock_db.put_item.call_count == 2
        call_args_list = mock_db.put_item.call_args_list

        # First call should be character
        char_call = call_args_list[0]
        assert "CHAR#" in char_call.args[1]

        # Second call should be session
        sess_call = call_args_list[1]
        assert "SESS#" in sess_call.args[1]


class TestGetClaudeClient:
    """Tests for lazy Claude client initialization."""

    def test_lazy_init_creates_client(self, mock_db):
        """_get_claude_client should create client on first call."""
        service = DMService(mock_db)  # No claude_client provided

        with patch("dm.service.get_claude_api_key", return_value="test-key"):
            with patch("dm.service.ClaudeClient") as mock_client_class:
                client = service._get_claude_client()

                mock_client_class.assert_called_once_with("test-key")
                assert client == mock_client_class.return_value

    def test_lazy_init_reuses_client(self, mock_db):
        """_get_claude_client should reuse client on subsequent calls."""
        service = DMService(mock_db)

        with patch("dm.service.get_claude_api_key", return_value="test-key"):
            with patch("dm.service.ClaudeClient") as mock_client_class:
                client1 = service._get_claude_client()
                client2 = service._get_claude_client()

                mock_client_class.assert_called_once()  # Only once
                assert client1 is client2
