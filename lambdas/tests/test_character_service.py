"""Tests for character service module."""

from unittest.mock import MagicMock, patch

import pytest

from character.models import CharacterCreateRequest, CharacterUpdateRequest
from character.service import CharacterService
from shared.exceptions import NotFoundError


@pytest.fixture
def mock_db():
    """Create a mock DynamoDB client."""
    return MagicMock()


@pytest.fixture
def service(mock_db):
    """Create a CharacterService with mocked DB."""
    return CharacterService(mock_db)


class TestCreateCharacter:
    """Tests for character creation."""

    def test_create_character_returns_character_data(self, service, mock_db):
        """Create character should return full character data."""
        request = CharacterCreateRequest(name="Thorin", character_class="fighter")

        with patch("character.service.generate_id", return_value="char-123"):
            with patch("character.service.utc_now", return_value="2026-01-01T00:00:00Z"):
                with patch("character.service.roll_ability_scores") as mock_roll:
                    mock_roll.return_value = {
                        "strength": 14,
                        "intelligence": 10,
                        "wisdom": 12,
                        "dexterity": 13,
                        "constitution": 15,
                        "charisma": 11,
                    }
                    with patch("character.service.roll_starting_hp", return_value=7):
                        with patch("character.service.roll_starting_gold", return_value=120):
                            result = service.create_character("user-123", request)

        assert result["character_id"] == "char-123"
        assert result["name"] == "Thorin"
        assert result["character_class"] == "fighter"
        assert result["level"] == 1
        assert result["xp"] == 0
        assert result["gold"] == 120
        # Fighter gets starting equipment
        assert len(result["inventory"]) > 0
        item_ids = [item["item_id"] for item in result["inventory"]]
        assert "sword" in item_ids
        assert "shield" in item_ids
        assert "chain_mail" in item_ids
        assert "Attack" in result["abilities"]
        assert "Parry" in result["abilities"]

    def test_create_character_calls_db_put(self, service, mock_db):
        """Create character should call db.put_item."""
        request = CharacterCreateRequest(name="Gandalf", character_class="magic_user")

        with patch("character.service.generate_id", return_value="char-456"):
            with patch("character.service.utc_now", return_value="2026-01-01T00:00:00Z"):
                service.create_character("user-123", request)

        mock_db.put_item.assert_called_once()
        call_args = mock_db.put_item.call_args
        assert call_args.kwargs["pk"] == "USER#user-123"
        assert call_args.kwargs["sk"] == "CHAR#char-456"

    def test_create_character_stats_are_valid(self, service, mock_db):
        """Created character stats should be in valid range."""
        request = CharacterCreateRequest(name="Test", character_class="cleric")

        result = service.create_character("user-123", request)

        for stat_name, stat_value in result["stats"].items():
            assert 3 <= stat_value <= 18, f"{stat_name} should be 3-18"

    def test_create_character_hp_is_positive(self, service, mock_db):
        """Created character HP should be at least 1."""
        request = CharacterCreateRequest(name="Test", character_class="thief")

        result = service.create_character("user-123", request)

        assert result["hp"] >= 1
        assert result["max_hp"] >= 1
        assert result["hp"] == result["max_hp"]

    def test_create_character_gold_is_valid(self, service, mock_db):
        """Created character gold should be 30-180."""
        request = CharacterCreateRequest(name="Test", character_class="fighter")

        result = service.create_character("user-123", request)

        assert 30 <= result["gold"] <= 180
        assert result["gold"] % 10 == 0

    def test_create_fighter_has_starting_equipment(self, service, mock_db):
        """Fighter gets sword, shield, chain mail."""
        request = CharacterCreateRequest(name="Warrior", character_class="fighter")
        result = service.create_character("user-123", request)

        item_ids = [item["item_id"] for item in result["inventory"]]
        assert "sword" in item_ids
        assert "shield" in item_ids
        assert "chain_mail" in item_ids
        assert "backpack" in item_ids

    def test_create_thief_has_starting_equipment(self, service, mock_db):
        """Thief gets dagger, leather armor, thieves' tools."""
        request = CharacterCreateRequest(name="Rogue", character_class="thief")
        result = service.create_character("user-123", request)

        item_ids = [item["item_id"] for item in result["inventory"]]
        assert "dagger" in item_ids
        assert "leather_armor" in item_ids
        assert "thieves_tools" in item_ids

    def test_create_cleric_has_starting_equipment(self, service, mock_db):
        """Cleric gets mace, shield, holy symbol."""
        request = CharacterCreateRequest(name="Priest", character_class="cleric")
        result = service.create_character("user-123", request)

        item_ids = [item["item_id"] for item in result["inventory"]]
        assert "mace" in item_ids
        assert "shield" in item_ids
        assert "holy_symbol" in item_ids
        assert "chain_mail" in item_ids

    def test_create_magic_user_has_starting_equipment(self, service, mock_db):
        """Magic user gets dagger, staff, spellbook, robes."""
        request = CharacterCreateRequest(name="Wizard", character_class="magic_user")
        result = service.create_character("user-123", request)

        item_ids = [item["item_id"] for item in result["inventory"]]
        assert "dagger" in item_ids
        assert "staff" in item_ids
        assert "spellbook" in item_ids
        assert "robes" in item_ids

    def test_create_character_inventory_has_proper_structure(self, service, mock_db):
        """Inventory items have complete structure."""
        request = CharacterCreateRequest(name="Test", character_class="fighter")
        result = service.create_character("user-123", request)

        for item in result["inventory"]:
            assert "item_id" in item
            assert "name" in item
            assert "quantity" in item
            assert "item_type" in item
            assert "description" in item


class TestListCharacters:
    """Tests for listing characters."""

    def test_list_characters_empty(self, service, mock_db):
        """List should return empty list when no characters."""
        mock_db.query_by_pk.return_value = []

        result = service.list_characters("user-123")

        assert result == []
        mock_db.query_by_pk.assert_called_once_with(
            pk="USER#user-123",
            sk_prefix="CHAR#",
        )

    def test_list_characters_returns_summaries(self, service, mock_db):
        """List should return character summaries only."""
        mock_db.query_by_pk.return_value = [
            {
                "character_id": "char-1",
                "name": "Thorin",
                "character_class": "fighter",
                "level": 3,
                "xp": 4000,
                "hp": 25,
                "max_hp": 25,
                "gold": 500,
                "stats": {"strength": 16},
                "inventory": [],
                "abilities": ["Attack"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ]

        result = service.list_characters("user-123")

        assert len(result) == 1
        assert result[0] == {
            "character_id": "char-1",
            "name": "Thorin",
            "character_class": "fighter",
            "level": 3,
            "created_at": "2026-01-01T00:00:00Z",
        }
        # Should NOT include full details
        assert "hp" not in result[0]
        assert "stats" not in result[0]
        assert "inventory" not in result[0]

    def test_list_characters_multiple(self, service, mock_db):
        """List should return multiple characters."""
        mock_db.query_by_pk.return_value = [
            {
                "character_id": "char-1",
                "name": "Thorin",
                "character_class": "fighter",
                "level": 1,
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "character_id": "char-2",
                "name": "Gandalf",
                "character_class": "magic_user",
                "level": 5,
                "created_at": "2026-01-02T00:00:00Z",
            },
        ]

        result = service.list_characters("user-123")

        assert len(result) == 2


class TestGetCharacter:
    """Tests for getting a single character."""

    def test_get_character_success(self, service, mock_db):
        """Get should return full character data."""
        mock_db.get_item_or_raise.return_value = {
            "PK": "USER#user-123",
            "SK": "CHAR#char-1",
            "character_id": "char-1",
            "name": "Thorin",
            "character_class": "fighter",
            "level": 1,
            "hp": 8,
        }

        result = service.get_character("user-123", "char-1")

        assert result["character_id"] == "char-1"
        assert result["name"] == "Thorin"
        assert "PK" not in result  # DB keys stripped
        assert "SK" not in result

    def test_get_character_not_found(self, service, mock_db):
        """Get should raise NotFoundError for missing character."""
        mock_db.get_item_or_raise.side_effect = NotFoundError("Character", "char-999")

        with pytest.raises(NotFoundError) as exc_info:
            service.get_character("user-123", "char-999")

        assert exc_info.value.resource_type == "Character"
        assert exc_info.value.resource_id == "char-999"


class TestUpdateCharacter:
    """Tests for updating a character."""

    def test_update_character_success(self, service, mock_db):
        """Update should change name and updated_at."""
        # First call for verification, second for returning updated
        mock_db.get_item_or_raise.side_effect = [
            {
                "PK": "USER#user-123",
                "SK": "CHAR#char-1",
                "character_id": "char-1",
                "name": "Thorin",
            },
            {
                "PK": "USER#user-123",
                "SK": "CHAR#char-1",
                "character_id": "char-1",
                "name": "Thorin the Brave",
                "updated_at": "2026-01-02T00:00:00Z",
            },
        ]

        request = CharacterUpdateRequest(name="Thorin the Brave")

        with patch("character.service.utc_now", return_value="2026-01-02T00:00:00Z"):
            result = service.update_character("user-123", "char-1", request)

        assert result["name"] == "Thorin the Brave"
        mock_db.update_item.assert_called_once()

    def test_update_character_not_found(self, service, mock_db):
        """Update should raise NotFoundError for missing character."""
        mock_db.get_item_or_raise.side_effect = NotFoundError("Item", "char-1")

        request = CharacterUpdateRequest(name="New Name")

        with pytest.raises(NotFoundError):
            service.update_character("user-123", "char-999", request)


class TestDeleteCharacter:
    """Tests for deleting a character."""

    def test_delete_character_success(self, service, mock_db):
        """Delete should call db.delete_item."""
        mock_db.get_item_or_raise.return_value = {
            "PK": "USER#user-123",
            "SK": "CHAR#char-1",
            "character_id": "char-1",
        }

        service.delete_character("user-123", "char-1")

        mock_db.delete_item.assert_called_once_with(
            pk="USER#user-123",
            sk="CHAR#char-1",
        )

    def test_delete_character_not_found(self, service, mock_db):
        """Delete should raise NotFoundError for missing character."""
        mock_db.get_item_or_raise.side_effect = NotFoundError("Item", "char-1")

        with pytest.raises(NotFoundError):
            service.delete_character("user-123", "char-999")

        mock_db.delete_item.assert_not_called()
