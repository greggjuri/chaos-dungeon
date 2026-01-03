"""Pydantic models for Chaos Dungeon game entities."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CharacterClass(str, Enum):
    """BECMI character classes."""

    FIGHTER = "fighter"
    THIEF = "thief"
    MAGIC_USER = "magic_user"
    CLERIC = "cleric"


class MessageRole(str, Enum):
    """Message sender role."""

    PLAYER = "player"
    DM = "dm"


class AbilityScores(BaseModel):
    """D&D ability scores (3-18 range)."""

    strength: int = Field(..., ge=3, le=18)
    intelligence: int = Field(..., ge=3, le=18)
    wisdom: int = Field(..., ge=3, le=18)
    dexterity: int = Field(..., ge=3, le=18)
    constitution: int = Field(..., ge=3, le=18)
    charisma: int = Field(..., ge=3, le=18)


class Item(BaseModel):
    """Inventory item."""

    name: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1)
    weight: float = Field(default=0.0, ge=0)
    description: str | None = None


class Message(BaseModel):
    """Game message in session history."""

    role: MessageRole
    content: str = Field(..., min_length=1)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class Character(BaseModel):
    """Player character model."""

    character_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    name: str = Field(..., min_length=1, max_length=50)
    character_class: CharacterClass
    level: int = Field(default=1, ge=1, le=36)
    xp: int = Field(default=0, ge=0)
    hp: int = Field(default=1, ge=0)
    max_hp: int = Field(default=1, ge=1)
    gold: int = Field(default=0, ge=0)
    abilities: AbilityScores
    inventory: list[Item] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None

    def to_db_keys(self) -> tuple[str, str]:
        """Get DynamoDB PK and SK for this character.

        Returns:
            Tuple of (PK, SK)
        """
        return f"USER#{self.user_id}", f"CHAR#{self.character_id}"

    def to_db_item(self) -> tuple[str, str, dict[str, Any]]:
        """Convert to DynamoDB item format.

        Returns:
            Tuple of (PK, SK, data dict)
        """
        pk, sk = self.to_db_keys()
        data = self.model_dump(exclude={"user_id", "character_id"})
        return pk, sk, data

    @classmethod
    def from_db_item(cls, item: dict[str, Any]) -> "Character":
        """Create Character from DynamoDB item.

        Args:
            item: DynamoDB item dict

        Returns:
            Character instance
        """
        user_id = item["PK"].replace("USER#", "")
        character_id = item["SK"].replace("CHAR#", "")
        return cls(
            user_id=user_id,
            character_id=character_id,
            **{k: v for k, v in item.items() if k not in ("PK", "SK")},
        )


class Session(BaseModel):
    """Game session with state."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    character_id: str
    campaign_setting: str = Field(default="default")
    current_location: str = Field(default="Unknown")
    world_state: dict[str, Any] = Field(default_factory=dict)
    message_history: list[Message] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None

    def to_db_keys(self) -> tuple[str, str]:
        """Get DynamoDB PK and SK for this session.

        Returns:
            Tuple of (PK, SK)
        """
        return f"USER#{self.user_id}", f"SESS#{self.session_id}"

    def to_db_item(self) -> tuple[str, str, dict[str, Any]]:
        """Convert to DynamoDB item format.

        Returns:
            Tuple of (PK, SK, data dict)
        """
        pk, sk = self.to_db_keys()
        data = self.model_dump(exclude={"user_id", "session_id"})
        # Convert message history to dict format for DynamoDB
        data["message_history"] = [msg.model_dump() for msg in self.message_history]
        return pk, sk, data

    @classmethod
    def from_db_item(cls, item: dict[str, Any]) -> "Session":
        """Create Session from DynamoDB item.

        Args:
            item: DynamoDB item dict

        Returns:
            Session instance
        """
        user_id = item["PK"].replace("USER#", "")
        session_id = item["SK"].replace("SESS#", "")
        # Convert message history from dict format
        message_history = [Message(**msg) for msg in item.get("message_history", [])]
        return cls(
            user_id=user_id,
            session_id=session_id,
            character_id=item["character_id"],
            campaign_setting=item.get("campaign_setting", "default"),
            current_location=item.get("current_location", "Unknown"),
            world_state=item.get("world_state", {}),
            message_history=message_history,
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
        )

    def add_message(self, role: MessageRole, content: str) -> Message:
        """Add a new message to the session history.

        Args:
            role: Who sent the message
            content: Message content

        Returns:
            The created Message
        """
        message = Message(role=role, content=content)
        self.message_history.append(message)
        return message
