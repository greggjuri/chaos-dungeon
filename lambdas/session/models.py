"""Pydantic models for session API request/response validation."""

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CampaignSetting(str, Enum):
    """Available campaign settings for new sessions."""

    DEFAULT = "default"
    DARK_FOREST = "dark_forest"
    CURSED_CASTLE = "cursed_castle"
    FORGOTTEN_MINES = "forgotten_mines"


class SessionCreateRequest(BaseModel):
    """Request body for creating a new session."""

    character_id: str = Field(..., min_length=36, max_length=36)
    campaign_setting: CampaignSetting = CampaignSetting.DEFAULT

    @field_validator("character_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that character_id is a valid UUID v4."""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, v.lower()):
            raise ValueError("character_id must be a valid UUID v4")
        return v
