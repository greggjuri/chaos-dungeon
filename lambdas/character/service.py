"""Character service - business logic for character CRUD operations."""

from aws_lambda_powertools import Logger

from character.models import CharacterCreateRequest, CharacterUpdateRequest
from shared.becmi import (
    CharacterClass,
    get_hit_dice,
    get_starting_abilities,
    roll_starting_gold,
    roll_starting_hp,
)
from shared.db import DynamoDBClient
from shared.items import get_starting_equipment
from shared.utils import (
    calculate_modifier,
    generate_id,
    roll_ability_scores,
    utc_now,
)

logger = Logger()


class CharacterService:
    """Service layer for character CRUD operations."""

    def __init__(self, db_client: DynamoDBClient) -> None:
        """Initialize character service.

        Args:
            db_client: DynamoDB client instance
        """
        self.db = db_client

    def create_character(self, user_id: str, request: CharacterCreateRequest) -> dict:
        """Create a new character with rolled stats.

        Args:
            user_id: The user's ID
            request: Character creation request

        Returns:
            The created character data
        """
        character_id = generate_id()
        now = utc_now()

        # Roll ability scores (3d6 for each)
        stats = roll_ability_scores()
        con_modifier = calculate_modifier(stats["constitution"])

        # Get class-specific values
        char_class = CharacterClass(request.character_class)
        hit_die = get_hit_dice(char_class)
        hp = roll_starting_hp(hit_die, con_modifier)
        abilities = get_starting_abilities(char_class)
        gold = roll_starting_gold()

        # Get class-appropriate starting equipment
        inventory = get_starting_equipment(request.character_class)

        character = {
            "character_id": character_id,
            "name": request.name,
            "character_class": request.character_class,
            "level": 1,
            "xp": 0,
            "hp": hp,
            "max_hp": hp,
            "gold": gold,
            "stats": stats,
            "inventory": inventory,
            "abilities": abilities,
            "created_at": now,
            "updated_at": now,
        }

        self.db.put_item(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{character_id}",
            data=character,
        )

        logger.info(
            "Character created",
            extra={
                "user_id": user_id,
                "character_id": character_id,
                "character_class": request.character_class,
            },
        )

        return character

    def list_characters(self, user_id: str) -> list[dict]:
        """List all characters for a user (summary only).

        Args:
            user_id: The user's ID

        Returns:
            List of character summaries
        """
        items = self.db.query_by_pk(
            pk=f"USER#{user_id}",
            sk_prefix="CHAR#",
        )

        return [
            {
                "character_id": item["character_id"],
                "name": item["name"],
                "character_class": item["character_class"],
                "level": item["level"],
                "created_at": item["created_at"],
            }
            for item in items
        ]

    def get_character(self, user_id: str, character_id: str) -> dict:
        """Get full character details.

        Args:
            user_id: The user's ID
            character_id: The character's ID

        Returns:
            Full character data

        Raises:
            NotFoundError: If character doesn't exist
        """
        item = self.db.get_item_or_raise(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{character_id}",
            resource_type="Character",
            resource_id=character_id,
        )
        # Remove DynamoDB keys from response
        return {k: v for k, v in item.items() if k not in ("PK", "SK")}

    def update_character(
        self, user_id: str, character_id: str, request: CharacterUpdateRequest
    ) -> dict:
        """Update character (name only for now).

        Args:
            user_id: The user's ID
            character_id: The character's ID
            request: Update request with new name

        Returns:
            Updated character data

        Raises:
            NotFoundError: If character doesn't exist
        """
        # Verify character exists first
        self.get_character(user_id, character_id)

        # Note: updated_at is set automatically by db.update_item
        self.db.update_item(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{character_id}",
            updates={"name": request.name},
        )

        logger.info(
            "Character updated",
            extra={
                "user_id": user_id,
                "character_id": character_id,
                "new_name": request.name,
            },
        )

        return self.get_character(user_id, character_id)

    def delete_character(self, user_id: str, character_id: str) -> None:
        """Delete a character.

        Args:
            user_id: The user's ID
            character_id: The character's ID

        Raises:
            NotFoundError: If character doesn't exist
        """
        # Verify character exists first
        self.get_character(user_id, character_id)

        self.db.delete_item(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{character_id}",
        )

        logger.info(
            "Character deleted",
            extra={
                "user_id": user_id,
                "character_id": character_id,
            },
        )
