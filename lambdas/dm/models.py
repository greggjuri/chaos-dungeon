"""Pydantic models for DM response parsing and action handling."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class StateChanges(BaseModel):
    """State changes to apply to game state after DM response.

    All fields are optional with sensible defaults, allowing
    partial updates from the DM response.
    """

    hp_delta: int = 0
    """Change in HP (negative for damage, positive for healing)."""

    gold_delta: int = 0
    """Change in gold (negative for spending, positive for looting)."""

    xp_delta: int = 0
    """XP gained this turn."""

    location: str | None = None
    """New location if the player moved."""

    inventory_add: list[str] = Field(default_factory=list)
    """Items added to inventory."""

    inventory_remove: list[str] = Field(default_factory=list)
    """Items removed from inventory."""

    world_state: dict[str, Any] = Field(default_factory=dict)
    """Permanent world state flags to set."""


class DiceRoll(BaseModel):
    """Record of a dice roll made by the DM.

    Captures the breakdown of a roll for display and logging.
    """

    type: str
    """Type of roll: attack, damage, save, skill, initiative, etc."""

    roll: int
    """Raw dice result (before modifiers)."""

    modifier: int = 0
    """Modifier applied to the roll."""

    total: int
    """Final result (roll + modifier)."""

    success: bool | None = None
    """Whether the roll succeeded (if applicable)."""


class Enemy(BaseModel):
    """Enemy state during combat.

    Tracks the current status of enemies in an encounter.
    """

    name: str
    """Enemy name/type."""

    hp: int
    """Current hit points."""

    ac: int
    """Armor class."""

    max_hp: int | None = None
    """Maximum HP (optional, for display)."""


class DMResponse(BaseModel):
    """Parsed DM response with narrative and state changes.

    The main output of parsing a DM's response, containing
    both the narrative text and structured game state updates.
    """

    narrative: str
    """The DM's narrative response text."""

    state_changes: StateChanges = Field(default_factory=StateChanges)
    """State changes to apply to the game."""

    dice_rolls: list[DiceRoll] = Field(default_factory=list)
    """Dice rolls made during this turn."""

    combat_active: bool = False
    """Whether combat is currently ongoing."""

    enemies: list[Enemy] = Field(default_factory=list)
    """Current enemy status (only during combat)."""


class ActionRequest(BaseModel):
    """Player action request."""

    action: str = Field(..., min_length=1, max_length=500)
    """The player's action text (1-500 chars)."""

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Strip whitespace from action."""
        return v.strip()


class CharacterSnapshot(BaseModel):
    """Character state to include in response."""

    hp: int
    """Current hit points."""

    max_hp: int
    """Maximum hit points."""

    xp: int
    """Current experience points."""

    gold: int
    """Current gold."""

    level: int
    """Character level."""

    inventory: list[str]
    """List of item names in inventory."""


class ActionResponse(BaseModel):
    """Full response to player action."""

    narrative: str
    """The DM's narrative response."""

    state_changes: StateChanges
    """State changes applied this turn."""

    dice_rolls: list[DiceRoll]
    """Dice rolls made during this turn."""

    combat_active: bool
    """Whether combat is ongoing."""

    enemies: list[Enemy]
    """Current enemy status (if in combat)."""

    character: CharacterSnapshot
    """Updated character state."""

    character_dead: bool = False
    """True if character died this turn."""

    session_ended: bool = False
    """True if session has ended."""
