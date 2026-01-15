"""Pydantic models for DM response parsing and action handling."""

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from shared.items import InventoryItem


class CombatPhase(str, Enum):
    """Combat state machine phases."""

    COMBAT_START = "combat_start"
    PLAYER_TURN = "player_turn"
    RESOLVE_PLAYER = "resolve_player"
    ENEMY_TURN = "enemy_turn"
    COMBAT_END = "combat_end"


class CombatActionType(str, Enum):
    """Player combat action types."""

    ATTACK = "attack"
    DEFEND = "defend"  # +2 AC this round
    FLEE = "flee"  # Dex check to escape
    USE_ITEM = "use_item"  # Potion, etc.


class CombatAction(BaseModel):
    """Player's chosen combat action."""

    action_type: CombatActionType
    target_id: str | None = None  # For attack actions
    item_id: str | None = None  # For use item actions


class CombatLogEntry(BaseModel):
    """Single entry in combat log."""

    round: int
    actor: str  # "player" or enemy ID/name
    action: str  # "attack", "defend", "flee"
    target: str | None = None
    roll: int | None = None  # Attack roll total
    damage: int | None = None
    result: str  # "hit", "miss", "killed", "fled", "defended"
    narrative: str = ""  # AI-generated description


class CommerceTransaction(BaseModel):
    """Buy transaction details from DM."""

    item: str
    """Item ID to purchase."""

    price: int = Field(ge=0)
    """Gold cost (should match catalog price)."""


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

    item_used: str | None = None
    """Item that was consumed this turn."""

    commerce_sell: str | None = None
    """Item ID to sell. Server removes from inventory, adds 50% value as gold."""

    commerce_buy: CommerceTransaction | None = None
    """Purchase request. Server validates gold, deducts, adds item."""


class DiceRoll(BaseModel):
    """Record of a dice roll made by the DM.

    Captures the breakdown of a roll for display and logging.
    """

    type: str
    """Type of roll: attack, damage, save, skill, initiative, etc."""

    dice: str = "d20"
    """Die used (e.g., 'd20', 'd8', 'd6')."""

    roll: int
    """Raw dice result (before modifiers)."""

    modifier: int = 0
    """Modifier applied to the roll."""

    total: int
    """Final result (roll + modifier)."""

    success: bool | None = None
    """Whether the roll succeeded (if applicable)."""

    attacker: str | None = None
    """Name of the attacker (for combat rolls)."""

    target: str | None = None
    """Name of the target (for combat rolls)."""


class Enemy(BaseModel):
    """Enemy state during combat (basic, from Claude response).

    Tracks the current status of enemies in an encounter.
    Used when parsing Claude's response for enemy info.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    """Unique ID for targeting (always generated if not provided)."""

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
    including initiative, round number, and phase.
    """

    active: bool = False
    """Whether combat is currently active."""

    round: int = 0
    """Current combat round number."""

    phase: CombatPhase = CombatPhase.PLAYER_TURN
    """Current phase in the combat state machine."""

    player_initiative: int = 0
    """Player's initiative roll for this combat."""

    enemy_initiative: int = 0
    """Enemies' initiative roll for this combat."""

    player_defending: bool = False
    """Whether player is defending (+2 AC) this round."""

    combat_log: list[CombatLogEntry] = Field(default_factory=list)
    """Log of all combat actions this encounter."""


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

    damage_dice: str = "1d6"
    """Damage dice notation used (e.g., '1d6', '1d8')."""

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

    action: str = Field(default="", max_length=500)
    """The player's action text (0-500 chars). Can be empty if combat_action provided."""

    combat_action: CombatAction | None = None
    """Structured combat action (takes precedence over free text action)."""

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Strip whitespace from action."""
        return v.strip()

    @model_validator(mode="after")
    def validate_has_action(self) -> "ActionRequest":
        """Ensure either action or combat_action is provided."""
        if not self.action and not self.combat_action:
            raise ValueError("Either action or combat_action must be provided")
        return self


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

    inventory: list[InventoryItem]
    """List of items in inventory."""


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


class CombatResponse(BaseModel):
    """Structured combat state for turn-based UI."""

    active: bool
    """Whether combat is ongoing."""

    round: int
    """Current round number."""

    phase: CombatPhase
    """Current combat phase."""

    your_hp: int
    """Player's current HP."""

    your_max_hp: int
    """Player's max HP."""

    enemies: list[dict[str, Any]]
    """Enemy status list as dicts to ensure id field is serialized."""

    available_actions: list[CombatActionType]
    """Actions player can take this turn."""

    valid_targets: list[str]
    """Enemy IDs that can be targeted."""

    combat_log: list[CombatLogEntry]
    """Recent combat log entries."""


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

    enemies: list[dict[str, Any]]
    """Current enemy status (if in combat) as dicts to ensure id field is serialized."""

    combat: CombatResponse | None = None
    """Structured combat state for turn-based UI (only during combat)."""

    character: CharacterSnapshot
    """Updated character state."""

    character_dead: bool = False
    """True if character died this turn."""

    session_ended: bool = False
    """True if session has ended."""

    usage: UsageStats | None = None
    """Token usage statistics (for debugging/monitoring)."""
