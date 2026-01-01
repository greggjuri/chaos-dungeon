"""Pydantic models for character API requests and responses."""
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CharacterCreateRequest(BaseModel):
    """Request body for creating a new character."""

    name: str = Field(..., min_length=3, max_length=30)
    character_class: str = Field(
        ..., pattern="^(fighter|thief|magic_user|cleric)$"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize character name."""
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9 ]+$", v):
            raise ValueError("Name must be alphanumeric with spaces only")
        if len(v) < 3:
            raise ValueError("Name must be at least 3 characters after trimming")
        return v


class CharacterUpdateRequest(BaseModel):
    """Request body for updating a character."""

    name: str = Field(..., min_length=3, max_length=30)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize character name."""
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9 ]+$", v):
            raise ValueError("Name must be alphanumeric with spaces only")
        if len(v) < 3:
            raise ValueError("Name must be at least 3 characters after trimming")
        return v


class CharacterSummary(BaseModel):
    """Summary view for character list."""

    character_id: str
    name: str
    character_class: str
    level: int
    created_at: str


class CharacterListResponse(BaseModel):
    """Response for GET /characters."""

    characters: list[CharacterSummary]


class CharacterResponse(BaseModel):
    """Full character response."""

    character_id: str
    name: str
    character_class: str
    level: int
    xp: int
    hp: int
    max_hp: int
    gold: int
    stats: dict[str, int]
    inventory: list[dict[str, Any]]
    abilities: list[str]
    created_at: str
    updated_at: str
