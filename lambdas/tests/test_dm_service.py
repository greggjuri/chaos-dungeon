"""Tests for DM service module."""

from unittest.mock import MagicMock, patch

import pytest

from dm.bedrock_client import MistralResponse
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
    response_text = """You swing your sword at the goblin, hitting it squarely!

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
    client.send_action.return_value = MistralResponse(
        text=response_text,
        input_tokens=100,
        output_tokens=50,
    )
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
            {"item_id": "sword", "name": "Sword", "quantity": 1, "item_type": "weapon", "description": "A trusty steel sword."},
            {"item_id": "shield", "name": "Shield", "quantity": 1, "item_type": "armor", "description": "A sturdy wooden shield."},
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

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["hp"] == 8

    def test_hp_delta_negative(self, service, sample_character, sample_session):
        """HP should decrease with negative delta."""
        dm_response = DMResponse(
            narrative="Ouch!",
            state_changes=StateChanges(hp_delta=-3),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["hp"] == 5

    def test_hp_cannot_exceed_max(self, service, sample_character, sample_session):
        """HP should not exceed max_hp."""
        dm_response = DMResponse(
            narrative="Full heal!",
            state_changes=StateChanges(hp_delta=100),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["hp"] == sample_character["max_hp"]

    def test_hp_cannot_go_below_zero(self, service, sample_character, sample_session):
        """HP should not go below 0."""
        dm_response = DMResponse(
            narrative="Critical hit!",
            state_changes=StateChanges(hp_delta=-100),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["hp"] == 0

    def test_gold_delta_positive(self, service, sample_character, sample_session):
        """Gold should increase with positive delta."""
        dm_response = DMResponse(
            narrative="Loot!",
            state_changes=StateChanges(gold_delta=50),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["gold"] == 150

    def test_gold_delta_negative(self, service, sample_character, sample_session):
        """Gold should decrease with negative delta."""
        dm_response = DMResponse(
            narrative="Paid",
            state_changes=StateChanges(gold_delta=-30),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["gold"] == 70

    def test_gold_cannot_go_negative(self, service, sample_character, sample_session):
        """Gold should not go below 0."""
        dm_response = DMResponse(
            narrative="Robbed!",
            state_changes=StateChanges(gold_delta=-1000),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["gold"] == 0

    def test_xp_delta(self, service, sample_character, sample_session):
        """XP should accumulate."""
        dm_response = DMResponse(
            narrative="Victory!",
            state_changes=StateChanges(xp_delta=100),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert char["xp"] == 100

    def test_inventory_add_valid_item(self, service, sample_character, sample_session):
        """Valid catalog items should be added to inventory."""
        dm_response = DMResponse(
            narrative="Found!",
            state_changes=StateChanges(inventory_add=["Potion of Healing", "Rusty Key"]),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        inventory_ids = [item["item_id"] for item in char["inventory"]]
        assert "potion_healing" in inventory_ids
        assert "rusty_key" in inventory_ids

    def test_inventory_add_with_alias(self, service, sample_character, sample_session):
        """Items via alias should be added correctly."""
        dm_response = DMResponse(
            narrative="Found a healing potion!",
            state_changes=StateChanges(inventory_add=["healing potion"]),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        inventory_ids = [item["item_id"] for item in char["inventory"]]
        assert "potion_healing" in inventory_ids

    def test_inventory_add_unknown_item_skipped(self, service, sample_character, sample_session):
        """Unknown items should be skipped with a warning."""
        dm_response = DMResponse(
            narrative="Found!",
            state_changes=StateChanges(inventory_add=["Vorpal Blade", "Dagger"]),
        )

        original_count = len(sample_character["inventory"])
        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        # Vorpal Blade is unknown, should be skipped
        # Dagger is valid, should be added
        assert len(char["inventory"]) == original_count + 1
        inventory_ids = [item["item_id"] for item in char["inventory"]]
        assert "dagger" in inventory_ids

    def test_inventory_add_dynamic_quest_item(self, service, sample_character, sample_session):
        """Quest items with keywords should be created dynamically."""
        dm_response = DMResponse(
            narrative="Found!",
            state_changes=StateChanges(inventory_add=["Ornate Locket"]),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        inventory_ids = [item["item_id"] for item in char["inventory"]]
        # Should have a quest item with locket in the id
        assert any("locket" in item_id for item_id in inventory_ids)

    def test_inventory_add_no_duplicates(self, service, sample_character, sample_session):
        """Duplicate items should not be added."""
        dm_response = DMResponse(
            narrative="Found!",
            state_changes=StateChanges(inventory_add=["Sword"]),  # Already has Sword
        )

        original_count = len(sample_character["inventory"])
        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert len(char["inventory"]) == original_count

    def test_inventory_remove(self, service, sample_character, sample_session):
        """Items should be removed from inventory."""
        dm_response = DMResponse(
            narrative="Used!",
            state_changes=StateChanges(inventory_remove=["Shield"]),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

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
        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert len(char["inventory"]) == 2  # Unchanged

    def test_inventory_remove_case_insensitive(self, service, sample_character, sample_session):
        """'shield' (lowercase) should remove 'Shield' (title case) from inventory."""
        dm_response = DMResponse(
            narrative="Dropped!",
            state_changes=StateChanges(inventory_remove=["shield"]),  # lowercase
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        inventory_names = [item["name"] for item in char["inventory"]]
        assert "Shield" not in inventory_names
        assert len(char["inventory"]) == 1  # Only Sword remains

    def test_inventory_remove_by_item_id(self, service, sample_character, sample_session):
        """Should be able to remove item by item_id."""
        dm_response = DMResponse(
            narrative="Dropped!",
            state_changes=StateChanges(inventory_remove=["sword"]),  # item_id not name
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        inventory_ids = [item["item_id"] for item in char["inventory"]]
        assert "sword" not in inventory_ids
        assert len(char["inventory"]) == 1  # Only Shield remains

    def test_inventory_remove_decrements_quantity(self, service, sample_character, sample_session):
        """Removing from qty > 1 should decrement quantity instead of removing item."""
        # Add item with quantity 7
        sample_character["inventory"].append({
            "item_id": "rations",
            "name": "Rations",
            "quantity": 7,
            "item_type": "consumable",
            "description": "A week's worth of trail rations.",
        })

        dm_response = DMResponse(
            narrative="Ate some rations",
            state_changes=StateChanges(inventory_remove=["rations"]),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        # Should still have rations but with qty 6
        rations = next((i for i in char["inventory"] if i["item_id"] == "rations"), None)
        assert rations is not None
        assert rations["quantity"] == 6

    def test_inventory_remove_at_quantity_one(self, service, sample_character, sample_session):
        """Removing at qty 1 should remove the item entirely."""
        dm_response = DMResponse(
            narrative="Dropped!",
            state_changes=StateChanges(inventory_remove=["Sword"]),
        )

        char, _ = service._apply_state_changes(sample_character, sample_session, dm_response)

        inventory_ids = [item["item_id"] for item in char["inventory"]]
        assert "sword" not in inventory_ids

    def test_location_update(self, service, sample_character, sample_session):
        """Location should be updated."""
        dm_response = DMResponse(
            narrative="Entered forest",
            state_changes=StateChanges(location="Dark Forest"),
        )

        _, session = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert session["current_location"] == "Dark Forest"

    def test_location_not_updated_when_none(self, service, sample_character, sample_session):
        """Location should not change when not specified."""
        dm_response = DMResponse(
            narrative="Stayed",
            state_changes=StateChanges(),
        )

        _, session = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert session["current_location"] == "Tavern"

    def test_world_state_merge(self, service, sample_character, sample_session):
        """World state should be merged."""
        dm_response = DMResponse(
            narrative="Found secret",
            state_changes=StateChanges(world_state={"found_treasure": True}),
        )

        _, session = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert session["world_state"]["met_bartender"] is True
        assert session["world_state"]["found_treasure"] is True

    def test_combat_active_set(self, service, sample_character, sample_session):
        """Combat active state should be set."""
        dm_response = DMResponse(
            narrative="Battle!",
            combat_active=True,
            enemies=[Enemy(name="Goblin", hp=5, ac=12)],
        )

        _, session = service._apply_state_changes(sample_character, sample_session, dm_response)

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

        _, session = service._apply_state_changes(sample_character, sample_session, dm_response)

        assert session["combat_active"] is False
        assert session["enemies"] == []


class TestHandleUseItem:
    """Tests for _handle_use_item method."""

    def test_use_healing_potion_heals_hp(self, service, sample_character):
        """Using healing potion should restore HP."""
        # Give character a healing potion
        sample_character["inventory"].append({
            "item_id": "potion_healing",
            "name": "Potion of Healing",
            "quantity": 1,
            "item_type": "consumable",
            "description": "Heals 1d8 HP.",
        })
        sample_character["hp"] = 3  # Low HP
        sample_character["max_hp"] = 8

        with patch("dm.service.roll_dice_notation", return_value=(5, [5])):
            result = service._handle_use_item(sample_character, "potion_healing", 1)

        assert result is not None
        assert result["healing"] == 5
        assert sample_character["hp"] == 8  # 3 + 5 = 8

    def test_use_healing_potion_removes_from_inventory(self, service, sample_character):
        """Using potion should remove it from inventory."""
        sample_character["inventory"].append({
            "item_id": "potion_healing",
            "name": "Potion of Healing",
            "quantity": 1,
            "item_type": "consumable",
            "description": "Heals 1d8 HP.",
        })
        sample_character["hp"] = 3

        with patch("dm.service.roll_dice_notation", return_value=(5, [5])):
            service._handle_use_item(sample_character, "potion_healing", 1)

        inventory_ids = [item["item_id"] for item in sample_character["inventory"]]
        assert "potion_healing" not in inventory_ids

    def test_use_item_decrements_quantity(self, service, sample_character):
        """Using item with quantity > 1 should decrement quantity."""
        sample_character["inventory"].append({
            "item_id": "potion_healing",
            "name": "Potion of Healing",
            "quantity": 3,
            "item_type": "consumable",
            "description": "Heals 1d8 HP.",
        })
        sample_character["hp"] = 3

        with patch("dm.service.roll_dice_notation", return_value=(5, [5])):
            service._handle_use_item(sample_character, "potion_healing", 1)

        potion = next(
            (item for item in sample_character["inventory"] if item["item_id"] == "potion_healing"),
            None
        )
        assert potion is not None
        assert potion["quantity"] == 2

    def test_use_item_healing_capped_at_max_hp(self, service, sample_character):
        """Healing should not exceed max HP."""
        sample_character["inventory"].append({
            "item_id": "potion_healing",
            "name": "Potion of Healing",
            "quantity": 1,
            "item_type": "consumable",
            "description": "Heals 1d8 HP.",
        })
        sample_character["hp"] = 7  # Near max
        sample_character["max_hp"] = 8

        with patch("dm.service.roll_dice_notation", return_value=(8, [8])):  # Roll max
            result = service._handle_use_item(sample_character, "potion_healing", 1)

        assert sample_character["hp"] == 8  # Capped at max
        assert result["healing"] == 1  # Only 1 HP actually restored

    def test_use_item_no_potion_returns_none(self, service, sample_character):
        """Using item without having potion should return None."""
        # No potion in inventory
        result = service._handle_use_item(sample_character, None, 1)

        assert result is None

    def test_use_item_auto_select_potion(self, service, sample_character):
        """Should auto-select healing potion if no item_id provided."""
        sample_character["inventory"].append({
            "item_id": "potion_healing",
            "name": "Potion of Healing",
            "quantity": 1,
            "item_type": "consumable",
            "description": "Heals 1d8 HP.",
        })
        sample_character["hp"] = 3
        sample_character["max_hp"] = 8

        with patch("dm.service.roll_dice_notation", return_value=(5, [5])):
            result = service._handle_use_item(sample_character, None, 1)

        assert result is not None
        assert result["healing"] == 5

    def test_use_item_creates_log_entry(self, service, sample_character):
        """Using item should create combat log entry."""
        sample_character["inventory"].append({
            "item_id": "potion_healing",
            "name": "Potion of Healing",
            "quantity": 1,
            "item_type": "consumable",
            "description": "Heals 1d8 HP.",
        })
        sample_character["hp"] = 3

        with patch("dm.service.roll_dice_notation", return_value=(5, [5])):
            result = service._handle_use_item(sample_character, "potion_healing", 1)

        assert len(result["log_entries"]) == 1
        assert result["log_entries"][0].action == "use_item"
        assert "healed" in result["log_entries"][0].result


class TestAppendMessages:
    """Tests for _append_messages method."""

    def test_append_messages_adds_player_and_dm(self, service, sample_session):
        """Should append player and DM messages."""
        with patch("dm.service.datetime") as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "2026-01-01T12:00:00Z"

            session = service._append_messages(sample_session, "I attack", "You swing your sword!")

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

    def test_process_action_success(self, service, mock_db, sample_session, sample_character):
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

    def test_process_action_character_not_found(self, service, mock_db, sample_session):
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
        response_text = """The dragon breathes fire, engulfing you in a torrent of flames!

```json
{
    "state_changes": {
        "hp_delta": -10
    }
}
```"""
        mock_claude_client.send_action.return_value = MistralResponse(
            text=response_text,
            input_tokens=50,
            output_tokens=30,
        )

        result = service.process_action(
            session_id="sess-123",
            user_id="user-123",
            action="I attack the dragon",
        )

        assert result.character_dead is True
        assert result.session_ended is True
        assert result.character.hp == 0

    def test_process_action_saves_updates(self, service, mock_db, sample_session, sample_character):
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


class TestCombatDeath:
    """Tests for character death in turn-based combat."""

    def test_combat_death_includes_dice_rolls(self, service, mock_db, sample_session, sample_character):
        """Combat death response should include dice_rolls from attack results."""
        # Set up combat state
        sample_character["hp"] = 1  # Low HP to guarantee death
        sample_session["combat_state"] = {
            "active": True,
            "round": 1,
            "phase": "player_turn",
            "player_initiative": 10,
            "enemy_initiative": 15,
            "player_defending": False,
            "combat_log": [],
        }
        sample_session["combat_enemies"] = [
            {
                "id": "goblin-1",
                "name": "Goblin",
                "hp": 5,
                "max_hp": 5,
                "ac": 12,
                "attack_bonus": 2,
                "damage_dice": "1d6",
                "xp_value": 25,
            }
        ]
        mock_db.get_item.side_effect = [sample_session, sample_character]

        # Mock AI narrative response
        service._ai_client = MagicMock()
        service._ai_client.narrate_combat.return_value = MistralResponse(
            text="The goblin strikes you down!",
            input_tokens=20,
            output_tokens=10,
        )

        # Process combat action - attacking will trigger enemy counterattack
        from dm.models import CombatAction, CombatActionType
        result = service.process_action(
            session_id="sess-123",
            user_id="user-123",
            action="I attack the goblin",
            combat_action=CombatAction(action_type=CombatActionType.ATTACK, target_id="goblin-1"),
        )

        # Character should be dead
        assert result.character_dead is True
        assert result.session_ended is True

        # dice_rolls should be populated with attack results
        assert result.dice_rolls is not None
        assert len(result.dice_rolls) > 0, "dice_rolls should contain attack rolls"

        # Check we have attack type dice rolls
        attack_rolls = [r for r in result.dice_rolls if r.type == "attack"]
        assert len(attack_rolls) > 0, "Should have at least one attack roll"

        # Verify attack roll structure
        for roll in attack_rolls:
            assert roll.roll >= 1, "Roll should be at least 1"
            assert roll.roll <= 20, "Roll should be at most 20"
            assert roll.attacker is not None, "Attacker should be set"
            assert roll.target is not None, "Target should be set"


class TestGetAIClient:
    """Tests for lazy AI client initialization."""

    def test_lazy_init_creates_mistral_client(self, mock_db):
        """_get_ai_client should create Bedrock client when MODEL_PROVIDER is mistral."""
        service = DMService(mock_db)  # No ai_client provided

        with patch("dm.service.MODEL_PROVIDER", "mistral"):
            with patch("dm.bedrock_client.boto3") as mock_boto3:
                client = service._get_ai_client()

                mock_boto3.client.assert_called_once()
                assert client is not None

    def test_lazy_init_creates_claude_client(self, mock_db):
        """_get_ai_client should create Claude client when MODEL_PROVIDER is claude."""
        service = DMService(mock_db)  # No ai_client provided

        with patch("dm.service.MODEL_PROVIDER", "claude"):
            with patch("shared.secrets.get_claude_api_key", return_value="test-key"):
                with patch("dm.claude_client.anthropic.Anthropic") as mock_anthropic:
                    client = service._get_ai_client()

                    mock_anthropic.assert_called_once_with(api_key="test-key")
                    assert client is not None

    def test_lazy_init_reuses_client(self, mock_db):
        """_get_ai_client should reuse client on subsequent calls."""
        service = DMService(mock_db)

        with patch("dm.service.MODEL_PROVIDER", "mistral"):
            with patch("dm.bedrock_client.boto3"):
                client1 = service._get_ai_client()
                client2 = service._get_ai_client()

                assert client1 is client2
