"""Pydantic models for DM response parsing and action handling."""

from typing import Any
from uuid import uuid4

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
    """Enemy state during combat (basic, from Claude response).

    Tracks the current status of enemies in an encounter.
    Used when parsing Claude's response for enemy info.
    """

    name: str
    """Enemy name/type."""

    hp: int
    """Current hit points."""

    ac: int
    """Armor class."""

    max_hp: int | None = None
    """Maximum HP (optional, for display)."""


class CombatState(BaseModel):
    """Active combat encounter state.

    Tracks the current state of an ongoing combat encounter,
    including initiative and round number.
    """

    active: bool = False
    """Whether combat is currently active."""

    round: int = 0
    """Current combat round number."""

    player_initiative: int = 0
    """Player's initiative roll for this combat."""

    enemy_initiative: int = 0
    """Enemies' initiative roll for this combat."""


class CombatEnemy(BaseModel):
    """Enemy with full combat stats for server-side resolution.

    Extends the basic Enemy with additional fields needed for
    mechanical combat resolution (attack bonus, damage dice, etc.).
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    """Unique ID for tracking individual enemies."""

    name: str
    """Enemy name/type."""

    hp: int
    """Current hit points."""

    max_hp: int
    """Maximum hit points."""

    ac: int
    """Armor class."""

    attack_bonus: int = 0
    """Bonus to attack rolls."""

    damage_dice: str = "1d6"
    """Damage dice notation (e.g., '1d6', '2d4+1')."""

    xp_value: int = 10
    """XP awarded when defeated."""


class AttackResult(BaseModel):
    """Result of a single attack.

    Captures all details of an attack roll for display and logging.
    """

    attacker: str
    """Name of the attacker."""

    defender: str
    """Name of the defender."""

    attack_roll: int
    """Natural d20 roll (before modifiers)."""

    attack_bonus: int
    """Modifier applied to the attack roll."""

    attack_total: int
    """Final attack roll (natural + bonus)."""

    target_ac: int
    """Target's armor class."""

    is_hit: bool
    """Whether the attack hit."""

    is_critical: bool = False
    """Whether this was a critical hit (natural 20)."""

    is_fumble: bool = False
    """Whether this was a fumble (natural 1)."""

    damage: int = 0
    """Damage dealt (0 if miss)."""

    damage_rolls: list[int] = Field(default_factory=list)
    """Individual damage dice results."""

    target_hp_before: int
    """Target's HP before this attack."""

    target_hp_after: int
    """Target's HP after this attack."""

    target_dead: bool = False
    """Whether this attack killed the target."""


class CombatRoundResult(BaseModel):
    """Result of a full combat round.

    Aggregates all attacks in a round and tracks combat state.
    """

    round: int
    """Round number."""

    attack_results: list[AttackResult]
    """All attacks that occurred this round."""

    player_hp: int
    """Player's HP after this round."""

    player_dead: bool
    """Whether the player died this round."""

    enemies_remaining: list[CombatEnemy]
    """Enemies still alive after this round."""

    combat_ended: bool
    """Whether combat ended this round."""

    xp_gained: int = 0
    """XP earned from kills this round."""


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


class UsageStats(BaseModel):
    """Token usage statistics for cost monitoring."""

    session_tokens: int
    """Total tokens used by this session today."""

    session_limit: int
    """Session daily token limit."""

    global_tokens: int
    """Total tokens used globally today."""

    global_limit: int
    """Global daily token limit."""


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

    usage: UsageStats | None = None
    """Token usage statistics (for debugging/monitoring)."""
