"""Tests for shared module."""
import pytest
from moto import mock_aws

from shared.config import Config, get_config
from shared.db import DynamoDBClient
from shared.exceptions import (
    ChaosDungeonError,
    ConfigurationError,
    GameStateError,
    NotFoundError,
    ValidationError,
)
from shared.models import (
    AbilityScores,
    Character,
    CharacterClass,
    Item,
    MessageRole,
    Session,
)
from shared.utils import (
    api_response,
    calculate_modifier,
    error_response,
    extract_user_id,
    generate_id,
    roll_ability_scores,
    roll_dice,
    utc_now,
)


class TestExceptions:
    """Tests for custom exceptions."""

    def test_chaos_dungeon_error(self):
        """Test base exception."""
        error = ChaosDungeonError("test message")
        assert str(error) == "test message"
        assert error.message == "test message"

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Character", "abc123")
        assert "Character" in str(error)
        assert "abc123" in str(error)
        assert error.resource_type == "Character"
        assert error.resource_id == "abc123"

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid value", field="name")
        assert "Invalid value" in str(error)
        assert error.field == "name"

    def test_game_state_error(self):
        """Test GameStateError."""
        error = GameStateError("Invalid transition", current_state="combat")
        assert "Invalid transition" in str(error)
        assert error.current_state == "combat"

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Missing config", config_key="TABLE_NAME")
        assert "Missing config" in str(error)
        assert error.config_key == "TABLE_NAME"


class TestConfig:
    """Tests for configuration module."""

    def test_config_from_env(self, env_setup):
        """Test loading config from environment."""
        config = Config.from_env()
        assert config.table_name == "test-table"
        assert config.environment == "test"
        assert config.log_level == "DEBUG"

    def test_config_is_production(self, env_setup):
        """Test is_production property."""
        import os
        os.environ["ENVIRONMENT"] = "prod"
        # Clear cache
        if hasattr(get_config, "_config"):
            delattr(get_config, "_config")
        config = Config.from_env()
        assert config.is_production is True

    def test_config_missing_table_name(self, env_setup):
        """Test error when TABLE_NAME is missing."""
        import os
        del os.environ["TABLE_NAME"]
        # Clear cache
        if hasattr(get_config, "_config"):
            delattr(get_config, "_config")
        with pytest.raises(ConfigurationError) as exc_info:
            Config.from_env()
        assert "TABLE_NAME" in str(exc_info.value)


class TestModels:
    """Tests for Pydantic models."""

    def test_ability_scores_valid(self):
        """Test valid ability scores."""
        scores = AbilityScores(
            strength=10,
            intelligence=12,
            wisdom=14,
            dexterity=16,
            constitution=8,
            charisma=18,
        )
        assert scores.strength == 10
        assert scores.charisma == 18

    def test_ability_scores_invalid(self):
        """Test invalid ability scores."""
        with pytest.raises(ValueError):
            AbilityScores(
                strength=2,  # Below minimum
                intelligence=12,
                wisdom=14,
                dexterity=16,
                constitution=8,
                charisma=18,
            )

    def test_character_creation(self):
        """Test character creation."""
        char = Character(
            user_id="user123",
            name="Aragorn",
            character_class=CharacterClass.FIGHTER,
            abilities=AbilityScores(
                strength=16,
                intelligence=10,
                wisdom=12,
                dexterity=14,
                constitution=15,
                charisma=13,
            ),
        )
        assert char.name == "Aragorn"
        assert char.character_class == CharacterClass.FIGHTER
        assert char.level == 1
        assert char.hp == 1
        assert len(char.character_id) > 0

    def test_character_db_serialization(self):
        """Test character to/from DynamoDB format."""
        char = Character(
            user_id="user123",
            character_id="char456",
            name="Gandalf",
            character_class=CharacterClass.MAGIC_USER,
            abilities=AbilityScores(
                strength=8,
                intelligence=18,
                wisdom=16,
                dexterity=10,
                constitution=12,
                charisma=14,
            ),
        )
        pk, sk, data = char.to_db_item()
        assert pk == "USER#user123"
        assert sk == "CHAR#char456"
        assert data["name"] == "Gandalf"
        assert "user_id" not in data
        assert "character_id" not in data

    def test_character_from_db(self):
        """Test creating character from DB item."""
        item = {
            "PK": "USER#user123",
            "SK": "CHAR#char456",
            "name": "Legolas",
            "character_class": "thief",
            "level": 5,
            "xp": 5000,
            "hp": 20,
            "max_hp": 25,
            "gold": 100,
            "abilities": {
                "strength": 12,
                "intelligence": 14,
                "wisdom": 10,
                "dexterity": 18,
                "constitution": 12,
                "charisma": 16,
            },
            "inventory": [],
            "created_at": "2025-01-01T00:00:00Z",
        }
        char = Character.from_db_item(item)
        assert char.user_id == "user123"
        assert char.character_id == "char456"
        assert char.name == "Legolas"
        assert char.level == 5

    def test_session_creation(self):
        """Test session creation."""
        session = Session(
            user_id="user123",
            character_id="char456",
        )
        assert session.user_id == "user123"
        assert session.character_id == "char456"
        assert session.current_location == "Unknown"
        assert len(session.message_history) == 0

    def test_session_add_message(self):
        """Test adding messages to session."""
        session = Session(
            user_id="user123",
            character_id="char456",
        )
        msg = session.add_message(MessageRole.PLAYER, "I search the room")
        assert msg.role == MessageRole.PLAYER
        assert msg.content == "I search the room"
        assert len(session.message_history) == 1

    def test_item_model(self):
        """Test item model."""
        item = Item(name="Sword", quantity=1, weight=3.0, description="A sharp sword")
        assert item.name == "Sword"
        assert item.weight == 3.0


class TestUtils:
    """Tests for utility functions."""

    def test_generate_id(self):
        """Test ID generation."""
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID format

    def test_utc_now(self):
        """Test timestamp generation."""
        timestamp = utc_now()
        assert "T" in timestamp
        assert timestamp.endswith("+00:00") or timestamp.endswith("Z")

    def test_extract_user_id(self):
        """Test user ID extraction from headers."""
        headers = {"X-User-Id": "user123", "Content-Type": "application/json"}
        user_id = extract_user_id(headers)
        assert user_id == "user123"

    def test_extract_user_id_case_insensitive(self):
        """Test user ID extraction is case-insensitive."""
        headers = {"x-user-id": "user456"}
        user_id = extract_user_id(headers)
        assert user_id == "user456"

    def test_extract_user_id_missing(self):
        """Test missing user ID returns None."""
        headers = {"Content-Type": "application/json"}
        user_id = extract_user_id(headers)
        assert user_id is None

    def test_api_response(self):
        """Test API response formatting."""
        response = api_response(200, {"data": "test"})
        assert response["statusCode"] == 200
        assert "application/json" in response["headers"]["Content-Type"]
        assert "test" in response["body"]

    def test_api_response_with_message(self):
        """Test API response with message only."""
        response = api_response(200, message="Success")
        assert response["statusCode"] == 200
        assert "Success" in response["body"]

    def test_error_response(self):
        """Test error response formatting."""
        response = error_response(400, "ValidationError", "Invalid input")
        assert response["statusCode"] == 400
        assert "ValidationError" in response["body"]
        assert "Invalid input" in response["body"]

    def test_roll_dice(self):
        """Test dice rolling."""
        results = roll_dice(3, 6)
        assert len(results) == 3
        assert all(1 <= r <= 6 for r in results)

    def test_roll_ability_scores(self):
        """Test ability score generation."""
        scores = roll_ability_scores()
        assert len(scores) == 6
        assert "strength" in scores
        assert "charisma" in scores
        assert all(3 <= s <= 18 for s in scores.values())

    def test_calculate_modifier(self):
        """Test ability modifier calculation."""
        assert calculate_modifier(3) == -3
        assert calculate_modifier(5) == -2
        assert calculate_modifier(8) == -1
        assert calculate_modifier(10) == 0
        assert calculate_modifier(14) == 1
        assert calculate_modifier(17) == 2
        assert calculate_modifier(18) == 3


class TestDynamoDBClient:
    """Tests for DynamoDB client."""

    @mock_aws
    def test_put_and_get_item(self, dynamodb_table):
        """Test putting and getting an item."""
        client = DynamoDBClient("test-table")

        data = {"name": "Test Character", "level": 1}
        client.put_item("USER#user1", "CHAR#char1", data)

        item = client.get_item("USER#user1", "CHAR#char1")
        assert item is not None
        assert item["name"] == "Test Character"
        assert "created_at" in item
        assert "updated_at" in item

    @mock_aws
    def test_get_nonexistent_item(self, dynamodb_table):
        """Test getting a non-existent item."""
        client = DynamoDBClient("test-table")
        item = client.get_item("USER#missing", "CHAR#missing")
        assert item is None

    @mock_aws
    def test_query_by_pk(self, dynamodb_table):
        """Test querying by partition key."""
        client = DynamoDBClient("test-table")

        client.put_item("USER#user1", "CHAR#char1", {"name": "Char 1"})
        client.put_item("USER#user1", "CHAR#char2", {"name": "Char 2"})
        client.put_item("USER#user2", "CHAR#char3", {"name": "Char 3"})

        items = client.query_by_pk("USER#user1", sk_prefix="CHAR#")
        assert len(items) == 2

    @mock_aws
    def test_delete_item(self, dynamodb_table):
        """Test deleting an item."""
        client = DynamoDBClient("test-table")

        client.put_item("USER#user1", "CHAR#char1", {"name": "To Delete"})
        result = client.delete_item("USER#user1", "CHAR#char1")
        assert result is True

        item = client.get_item("USER#user1", "CHAR#char1")
        assert item is None

    @mock_aws
    def test_delete_nonexistent_item(self, dynamodb_table):
        """Test deleting a non-existent item."""
        client = DynamoDBClient("test-table")
        result = client.delete_item("USER#missing", "CHAR#missing")
        assert result is False

    @mock_aws
    def test_update_item(self, dynamodb_table):
        """Test updating an item."""
        client = DynamoDBClient("test-table")

        client.put_item("USER#user1", "CHAR#char1", {"name": "Original", "level": 1})
        updated = client.update_item("USER#user1", "CHAR#char1", {"level": 2})

        assert updated is not None
        assert updated["level"] == 2
        assert updated["name"] == "Original"

    @mock_aws
    def test_get_item_or_raise(self, dynamodb_table):
        """Test get_item_or_raise method."""
        client = DynamoDBClient("test-table")

        client.put_item("USER#user1", "CHAR#char1", {"name": "Test"})

        item = client.get_item_or_raise("USER#user1", "CHAR#char1", "Character", "char1")
        assert item["name"] == "Test"

        with pytest.raises(NotFoundError) as exc_info:
            client.get_item_or_raise("USER#missing", "CHAR#missing", "Character", "missing")
        assert exc_info.value.resource_type == "Character"
