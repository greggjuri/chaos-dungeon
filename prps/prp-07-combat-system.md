# PRP-07: Server-Side Combat Resolution

**Created**: 2026-01-02
**Initial**: `initials/init-07-combat-system.md`
**Status**: Draft

---

## Overview

### Problem Statement
Currently, Claude (the AI DM) adjudicates all combat, consistently fudging rolls in the player's favor. This makes character death impossible and defeats the core design of a permadeath roguelike where death is expected and meaningful.

The trust model is broken: Claude decides outcomes instead of narrating mechanical results.

### Proposed Solution
Move all dice rolling and combat resolution to the server. The flow becomes:

1. Player submits combat action
2. Server detects combat state and resolves mechanically (d20 + modifiers vs AC)
3. Server applies damage and checks for death
4. Server tells Claude the outcome
5. Claude narrates the predetermined result (cannot change it)

This ensures fair, consistent combat with real stakes.

### Success Criteria
- [ ] All dice rolls happen server-side with Python `random`
- [ ] Attack resolution follows BECMI rules (d20 + mod vs AC)
- [ ] Damage rolled server-side with proper weapon dice
- [ ] Claude receives outcomes to narrate, not choices to make
- [ ] Character HP correctly reflects actual damage taken
- [ ] Character death triggers when HP ≤ 0
- [ ] Enemy death awards XP and removes from combat
- [ ] Combat state persists in session
- [ ] Initiative determines attack order each round
- [ ] All combat functions have 80%+ test coverage

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview, BECMI rules reference
- `docs/DECISIONS.md` - ADR-003 (BECMI rules), ADR-006 (prompt caching)
- `lambdas/dm/prompts/rules.py` - Existing BECMI rules in system prompt

### Dependencies
- **Required**: PRP-06 (Action Handler) - Current action flow ✓ Complete
- **Required**: PRP-05 (DM System Prompt) - Prompt structure ✓ Complete
- **Optional**: None

### Files to Modify/Create
```
lambdas/
├── shared/
│   └── dice.py              # NEW: Advanced dice notation parser
├── dm/
│   ├── combat.py            # NEW: Combat resolution service
│   ├── bestiary.py          # NEW: Enemy stat blocks
│   ├── models.py            # MODIFY: Add combat-related models
│   ├── service.py           # MODIFY: Integrate combat resolution
│   └── prompts/
│       └── combat_prompt.py # NEW: Combat narration templates
├── tests/
│   ├── test_dice.py         # NEW: Dice rolling tests
│   ├── test_combat.py       # NEW: Combat resolution tests
│   └── test_bestiary.py     # NEW: Bestiary tests
```

---

## Technical Specification

### Data Models

#### New Models (in `dm/models.py`)

```python
class CombatState(BaseModel):
    """Active combat encounter state."""
    active: bool = False
    round: int = 0
    player_initiative: int = 0
    enemy_initiative: int = 0

class CombatEnemy(BaseModel):
    """Enemy with full combat stats (extends existing Enemy)."""
    id: str  # UUID for tracking individual enemies
    name: str
    hp: int
    max_hp: int
    ac: int
    attack_bonus: int = 0
    damage_dice: str = "1d6"  # Standard notation
    xp_value: int = 10

class AttackResult(BaseModel):
    """Result of a single attack."""
    attacker: str
    defender: str
    attack_roll: int  # Natural d20 roll
    attack_bonus: int
    attack_total: int
    target_ac: int
    is_hit: bool
    is_critical: bool = False  # Natural 20
    is_fumble: bool = False    # Natural 1
    damage: int = 0
    damage_rolls: list[int] = []
    target_hp_before: int
    target_hp_after: int
    target_dead: bool = False

class CombatRoundResult(BaseModel):
    """Result of a full combat round."""
    round: int
    attack_results: list[AttackResult]
    player_hp: int
    player_dead: bool
    enemies_remaining: list[CombatEnemy]
    combat_ended: bool
    xp_gained: int = 0
```

#### Session Updates

Add to session storage:
```python
# In session dict
{
    "combat_state": {
        "active": True,
        "round": 1,
        "player_initiative": 4,
        "enemy_initiative": 2
    },
    "combat_enemies": [
        {
            "id": "uuid",
            "name": "Goblin",
            "hp": 4,
            "max_hp": 6,
            "ac": 12,
            "attack_bonus": 1,
            "damage_dice": "1d6",
            "xp_value": 10
        }
    ]
}
```

### New Module: Dice Rolling (`shared/dice.py`)

```python
def roll(notation: str) -> tuple[int, list[int]]:
    """Parse and roll standard dice notation.

    Supports: "1d20", "2d6+3", "1d8-1", "3d6"

    Returns: (total, individual_rolls)
    """

def roll_attack(attack_bonus: int) -> tuple[int, int]:
    """Roll d20 attack.

    Returns: (total, natural_roll)
    """

def roll_initiative() -> int:
    """Roll d6 for BECMI initiative."""
```

### New Module: Combat Resolution (`dm/combat.py`)

```python
class CombatResolver:
    """Server-side combat resolution following BECMI rules."""

    def resolve_player_attack(
        self,
        character: dict,
        target: CombatEnemy,
    ) -> AttackResult:
        """Resolve player attacking enemy."""

    def resolve_enemy_attack(
        self,
        enemy: CombatEnemy,
        character: dict,
    ) -> AttackResult:
        """Resolve enemy attacking player."""

    def resolve_combat_round(
        self,
        character: dict,
        combat_state: CombatState,
        combat_enemies: list[CombatEnemy],
    ) -> CombatRoundResult:
        """Resolve full combat round based on initiative."""

    def calculate_player_ac(self, character: dict) -> int:
        """Calculate player AC from equipment/DEX."""

    def get_weapon_damage(self, character: dict) -> str:
        """Get weapon damage dice from equipped weapon."""
```

### New Module: Bestiary (`dm/bestiary.py`)

```python
BESTIARY: dict[str, dict] = {
    "goblin": {
        "name": "Goblin",
        "hp_dice": "1d6",
        "ac": 12,
        "attack_bonus": 1,
        "damage_dice": "1d6",
        "xp_value": 10,
    },
    "skeleton": {...},
    "orc": {...},
    "wolf": {...},
    "zombie": {...},
    "giant_spider": {...},
    "vampire": {...},  # High-level threat
}

def spawn_enemy(enemy_type: str) -> CombatEnemy:
    """Create enemy instance with rolled HP."""
```

### API Changes

No API endpoint changes. Combat is handled transparently within the existing action flow:
- `POST /sessions/{id}/action` remains unchanged
- Response structure unchanged (already has `combat_active`, `enemies`, `dice_rolls`)

### Updated DM Prompt Flow

When combat is active, instead of asking Claude to decide outcomes, send:

```
## COMBAT OUTCOME (NARRATE THIS EXACTLY)

The following combat has been mechanically resolved. Your job is ONLY to
narrate what happened in dramatic fashion. You CANNOT change the outcome.

Round 1:

PLAYER ATTACK:
- Grimjaw attacks Goblin with sword
- Roll: d20(7) + 2 = 9 vs AC 12
- MISS - The attack fails to connect

ENEMY ATTACK:
- Goblin attacks Grimjaw with rusty blade
- Roll: d20(18) + 1 = 19 vs AC 14
- HIT - Damage: 1d6(5) = 5 HP
- Grimjaw takes 5 damage

FINAL STATE:
- Player HP: 3/8
- Player Status: Wounded
- Enemies: Goblin (4/4 HP)

Narrate this combat round with vivid detail. If the player died, describe
their death dramatically. Do not soften or change the outcome.
```

---

## Implementation Steps

### Step 1: Create Dice Rolling Module
**Files**: `lambdas/shared/dice.py`, `lambdas/tests/test_dice.py`

Create comprehensive dice notation parser and roller.

```python
# lambdas/shared/dice.py
import random
import re

def roll(notation: str) -> tuple[int, list[int]]:
    """Roll dice using standard notation (e.g., '2d6+3')."""
    pattern = r'^(\d+)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, notation.lower().replace(" ", ""))
    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3) or 0)

    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier

    return total, rolls
```

**Validation**:
- [ ] `pytest tests/test_dice.py` passes
- [ ] Distribution tests verify randomness
- [ ] Edge cases handled (invalid notation, 0 dice)

### Step 2: Create Combat Models
**Files**: `lambdas/dm/models.py`

Add new Pydantic models for combat state tracking.

```python
# Add to dm/models.py
class CombatState(BaseModel):
    """Active combat encounter state."""
    active: bool = False
    round: int = 0
    player_initiative: int = 0
    enemy_initiative: int = 0

class CombatEnemy(BaseModel):
    """Enemy with full combat stats."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    hp: int
    max_hp: int
    ac: int
    attack_bonus: int = 0
    damage_dice: str = "1d6"
    xp_value: int = 10

class AttackResult(BaseModel):
    """Result of a single attack."""
    # ... as specified above

class CombatRoundResult(BaseModel):
    """Result of a full combat round."""
    # ... as specified above
```

**Validation**:
- [ ] Models validate correctly
- [ ] Serialization/deserialization works

### Step 3: Create Bestiary Module
**Files**: `lambdas/dm/bestiary.py`, `lambdas/tests/test_bestiary.py`

Define enemy stat blocks and spawn function.

```python
# lambdas/dm/bestiary.py
from uuid import uuid4
from shared.dice import roll
from dm.models import CombatEnemy

BESTIARY = {
    "goblin": {
        "name": "Goblin",
        "hp_dice": "1d6",
        "ac": 12,
        "attack_bonus": 1,
        "damage_dice": "1d6",
        "xp_value": 10,
    },
    # ... more enemies
}

def spawn_enemy(enemy_type: str) -> CombatEnemy:
    """Create an enemy instance with rolled HP."""
    template = BESTIARY.get(enemy_type.lower())
    if not template:
        raise ValueError(f"Unknown enemy type: {enemy_type}")

    hp, _ = roll(template["hp_dice"])
    hp = max(1, hp)  # Minimum 1 HP

    return CombatEnemy(
        id=str(uuid4()),
        name=template["name"],
        hp=hp,
        max_hp=hp,
        ac=template["ac"],
        attack_bonus=template["attack_bonus"],
        damage_dice=template["damage_dice"],
        xp_value=template["xp_value"],
    )
```

**Validation**:
- [ ] All enemy types spawn correctly
- [ ] HP rolls within expected range
- [ ] Unknown enemies raise ValueError

### Step 4: Create Combat Resolution Service
**Files**: `lambdas/dm/combat.py`, `lambdas/tests/test_combat.py`

Implement the core combat resolution logic.

```python
# lambdas/dm/combat.py
from shared.dice import roll, roll_attack
from shared.utils import calculate_modifier
from dm.models import AttackResult, CombatEnemy, CombatRoundResult, CombatState

class CombatResolver:
    """Server-side combat resolution following BECMI rules."""

    def resolve_player_attack(
        self,
        character: dict,
        target: CombatEnemy,
    ) -> AttackResult:
        """Resolve player attacking enemy."""
        # Get STR modifier for melee
        str_mod = calculate_modifier(character["stats"]["strength"])
        attack_bonus = str_mod  # Could add level bonuses later

        # Roll attack
        total, natural = self._roll_attack(attack_bonus)
        is_hit = natural != 1 and (natural == 20 or total >= target.ac)
        is_crit = natural == 20
        is_fumble = natural == 1

        damage = 0
        damage_rolls = []
        hp_before = target.hp

        if is_hit:
            # Roll damage
            damage, damage_rolls = roll(self._get_weapon_damage(character))
            damage = max(1, damage + str_mod)  # Min 1 damage
            target.hp = max(0, target.hp - damage)

        return AttackResult(
            attacker=character["name"],
            defender=target.name,
            attack_roll=natural,
            attack_bonus=attack_bonus,
            attack_total=total,
            target_ac=target.ac,
            is_hit=is_hit,
            is_critical=is_crit,
            is_fumble=is_fumble,
            damage=damage,
            damage_rolls=damage_rolls,
            target_hp_before=hp_before,
            target_hp_after=target.hp,
            target_dead=target.hp <= 0,
        )

    def resolve_enemy_attack(
        self,
        enemy: CombatEnemy,
        character: dict,
    ) -> AttackResult:
        """Resolve enemy attacking player."""
        player_ac = self._calculate_player_ac(character)

        total, natural = self._roll_attack(enemy.attack_bonus)
        is_hit = natural != 1 and (natural == 20 or total >= player_ac)
        is_crit = natural == 20
        is_fumble = natural == 1

        damage = 0
        damage_rolls = []
        hp_before = character["hp"]

        if is_hit:
            damage, damage_rolls = roll(enemy.damage_dice)
            damage = max(1, damage)

        return AttackResult(
            attacker=enemy.name,
            defender=character["name"],
            attack_roll=natural,
            attack_bonus=enemy.attack_bonus,
            attack_total=total,
            target_ac=player_ac,
            is_hit=is_hit,
            is_critical=is_crit,
            is_fumble=is_fumble,
            damage=damage,
            damage_rolls=damage_rolls,
            target_hp_before=hp_before,
            target_hp_after=max(0, hp_before - damage) if is_hit else hp_before,
            target_dead=(hp_before - damage) <= 0 if is_hit else False,
        )

    def resolve_combat_round(
        self,
        character: dict,
        combat_state: CombatState,
        combat_enemies: list[CombatEnemy],
    ) -> CombatRoundResult:
        """Resolve full combat round based on initiative."""
        results = []
        xp_gained = 0

        player_first = combat_state.player_initiative >= combat_state.enemy_initiative
        living_enemies = [e for e in combat_enemies if e.hp > 0]

        if player_first:
            # Player attacks first
            if living_enemies:
                target = living_enemies[0]  # Attack first enemy
                result = self.resolve_player_attack(character, target)
                results.append(result)
                if result.target_dead:
                    xp_gained += target.xp_value

            # Surviving enemies counterattack
            for enemy in living_enemies:
                if enemy.hp > 0 and character["hp"] > 0:
                    result = self.resolve_enemy_attack(enemy, character)
                    results.append(result)
                    if result.is_hit:
                        character["hp"] = result.target_hp_after
        else:
            # Enemies attack first
            for enemy in living_enemies:
                if character["hp"] > 0:
                    result = self.resolve_enemy_attack(enemy, character)
                    results.append(result)
                    if result.is_hit:
                        character["hp"] = result.target_hp_after

            # Player counterattacks if alive
            if character["hp"] > 0 and living_enemies:
                target = living_enemies[0]
                result = self.resolve_player_attack(character, target)
                results.append(result)
                if result.target_dead:
                    xp_gained += target.xp_value

        # Update living enemies list
        remaining = [e for e in combat_enemies if e.hp > 0]

        return CombatRoundResult(
            round=combat_state.round,
            attack_results=results,
            player_hp=character["hp"],
            player_dead=character["hp"] <= 0,
            enemies_remaining=remaining,
            combat_ended=len(remaining) == 0 or character["hp"] <= 0,
            xp_gained=xp_gained,
        )

    def _roll_attack(self, bonus: int) -> tuple[int, int]:
        """Roll d20 attack. Returns (total, natural)."""
        import random
        natural = random.randint(1, 20)
        return natural + bonus, natural

    def _calculate_player_ac(self, character: dict) -> int:
        """Calculate player AC. Base 10 + DEX modifier."""
        dex_mod = calculate_modifier(character["stats"]["dexterity"])
        # TODO: Add armor bonuses from inventory
        return 10 + dex_mod

    def _get_weapon_damage(self, character: dict) -> str:
        """Get weapon damage dice. Default 1d6 for now."""
        # TODO: Look up equipped weapon
        return "1d6"
```

**Validation**:
- [ ] Player attacks resolve correctly
- [ ] Enemy attacks resolve correctly
- [ ] Initiative order works correctly
- [ ] Death detection works
- [ ] XP awarded on enemy death

### Step 5: Create Combat Prompt Builder
**Files**: `lambdas/dm/prompts/combat_prompt.py`

Build prompts that tell Claude the mechanical outcome.

```python
# lambdas/dm/prompts/combat_prompt.py

def build_combat_outcome_prompt(
    round_result: CombatRoundResult,
    player_max_hp: int,
) -> str:
    """Build prompt telling Claude what happened."""
    lines = [
        "## COMBAT OUTCOME (NARRATE THIS EXACTLY)",
        "",
        "The following combat has been mechanically resolved. Your job is ONLY to",
        "narrate what happened in dramatic fashion. You CANNOT change the outcome.",
        "",
        f"Round {round_result.round}:",
        "",
    ]

    for attack in round_result.attack_results:
        lines.append(_format_attack(attack))
        lines.append("")

    # Final state
    if round_result.player_dead:
        status = "DEAD"
    elif round_result.player_hp < player_max_hp // 2:
        status = "Badly wounded"
    elif round_result.player_hp < player_max_hp:
        status = "Wounded"
    else:
        status = "Unharmed"

    lines.extend([
        "FINAL STATE:",
        f"- Player HP: {round_result.player_hp}/{player_max_hp}",
        f"- Player Status: {status}",
    ])

    if round_result.enemies_remaining:
        enemy_status = ", ".join(
            f"{e.name} ({e.hp}/{e.max_hp} HP)"
            for e in round_result.enemies_remaining
        )
    else:
        enemy_status = "All enemies defeated"

    lines.append(f"- Enemies: {enemy_status}")
    lines.append("")

    if round_result.player_dead:
        lines.append(
            "Narrate this character's death dramatically. They are dead. "
            "Do not soften or change the outcome."
        )
    elif round_result.combat_ended:
        lines.append(
            "Narrate the end of combat. Victory or defeat, describe it vividly."
        )
    else:
        lines.append(
            "Narrate this combat round with vivid detail."
        )

    return "\n".join(lines)

def _format_attack(attack: AttackResult) -> str:
    """Format a single attack result."""
    lines = [f"{attack.attacker.upper()} ATTACK:"]
    lines.append(f"- {attack.attacker} attacks {attack.defender}")
    lines.append(
        f"- Roll: d20({attack.attack_roll}) + {attack.attack_bonus} = "
        f"{attack.attack_total} vs AC {attack.target_ac}"
    )

    if attack.is_fumble:
        lines.append("- FUMBLE - Critical failure!")
    elif attack.is_critical:
        lines.append(f"- CRITICAL HIT - Damage: {attack.damage} HP")
    elif attack.is_hit:
        damage_str = "+".join(str(d) for d in attack.damage_rolls)
        lines.append(f"- HIT - Damage: {damage_str} = {attack.damage} HP")
    else:
        lines.append("- MISS - The attack fails to connect")

    if attack.target_dead:
        lines.append(f"- {attack.defender} is SLAIN!")
    elif attack.is_hit:
        lines.append(f"- {attack.defender} HP: {attack.target_hp_after}")

    return "\n".join(lines)
```

**Validation**:
- [ ] Prompts format correctly
- [ ] All attack types represented
- [ ] Death narrative triggers correctly

### Step 6: Integrate Combat into DMService
**Files**: `lambdas/dm/service.py`

Modify `process_action` to detect and handle combat.

```python
# In dm/service.py - modifications

from dm.combat import CombatResolver
from dm.bestiary import spawn_enemy
from dm.prompts.combat_prompt import build_combat_outcome_prompt
from shared.dice import roll as roll_dice_notation

class DMService:
    def __init__(self, ...):
        # ... existing init
        self.combat_resolver = CombatResolver()

    def process_action(self, session_id, user_id, action) -> ActionResponse:
        # ... existing session/character loading ...

        # Check if we're in combat
        combat_state = session.get("combat_state", {})
        combat_enemies = session.get("combat_enemies", [])

        if combat_state.get("active"):
            # Resolve combat mechanically
            return self._process_combat_action(
                session, character, action, combat_state, combat_enemies
            )
        else:
            # Normal action processing (may initiate combat)
            return self._process_normal_action(session, character, action)

    def _process_combat_action(self, session, character, action,
                                combat_state, combat_enemies) -> ActionResponse:
        """Process action during active combat."""
        # Convert enemy dicts to models
        enemies = [CombatEnemy(**e) for e in combat_enemies]
        state = CombatState(**combat_state)
        state.round += 1

        # Resolve combat mechanically
        result = self.combat_resolver.resolve_combat_round(
            character, state, enemies
        )

        # Build outcome prompt for Claude
        outcome_prompt = build_combat_outcome_prompt(
            result, character["max_hp"]
        )

        # Get narrative from Claude (it can only narrate, not decide)
        system_prompt = self.prompt_builder.build_system_prompt(
            session.get("campaign_setting", "default")
        )
        narrative = self._get_claude_client().send_action(
            system_prompt,
            outcome_prompt,  # This tells Claude what happened
            action
        )

        # Apply results
        character["hp"] = result.player_hp
        character["xp"] += result.xp_gained

        # Update combat state
        if result.combat_ended:
            session["combat_state"] = {"active": False, "round": 0}
            session["combat_enemies"] = []
        else:
            session["combat_state"] = state.model_dump()
            session["combat_enemies"] = [e.model_dump() for e in enemies if e.hp > 0]

        # ... rest of save logic ...
```

**Validation**:
- [ ] Combat actions resolved mechanically
- [ ] Claude receives outcome, not choices
- [ ] State updates correctly
- [ ] Death triggers session end

### Step 7: Combat Initiation Logic
**Files**: `lambdas/dm/service.py`

Add logic to initiate combat when Claude's response includes enemies.

```python
def _process_normal_action(self, session, character, action) -> ActionResponse:
    # ... existing Claude call ...
    dm_response = parse_dm_response(raw_response)

    # Check if Claude initiated combat
    if dm_response.combat_active and dm_response.enemies:
        self._initiate_combat(session, dm_response.enemies)

    # ... rest of existing logic ...

def _initiate_combat(self, session: dict, enemies: list[Enemy]) -> None:
    """Start combat with enemies from Claude's response."""
    from shared.dice import roll as roll_dice_notation

    # Try to spawn enemies from bestiary, fallback to basic stats
    combat_enemies = []
    for enemy in enemies:
        try:
            spawned = spawn_enemy(enemy.name)
            combat_enemies.append(spawned.model_dump())
        except ValueError:
            # Unknown enemy - use stats from Claude's response
            combat_enemies.append({
                "id": str(uuid4()),
                "name": enemy.name,
                "hp": enemy.hp,
                "max_hp": enemy.max_hp or enemy.hp,
                "ac": enemy.ac,
                "attack_bonus": 1,
                "damage_dice": "1d6",
                "xp_value": max(10, enemy.hp * 2),  # Rough XP estimate
            })

    # Roll initiative
    player_init, _ = roll_dice_notation("1d6")
    enemy_init, _ = roll_dice_notation("1d6")

    session["combat_state"] = {
        "active": True,
        "round": 0,
        "player_initiative": player_init,
        "enemy_initiative": enemy_init,
    }
    session["combat_enemies"] = combat_enemies
```

**Validation**:
- [ ] Combat starts when enemies appear
- [ ] Bestiary enemies use proper stats
- [ ] Unknown enemies get reasonable defaults
- [ ] Initiative rolled correctly

### Step 8: Write Comprehensive Tests
**Files**: `lambdas/tests/test_dice.py`, `lambdas/tests/test_combat.py`, `lambdas/tests/test_bestiary.py`

Write tests with seeded random for determinism.

```python
# tests/test_combat.py example
import random
import pytest
from dm.combat import CombatResolver
from dm.models import CombatEnemy, CombatState

class TestCombatResolver:
    def test_player_hit_kills_enemy(self):
        """Player should kill enemy on hit when damage >= HP."""
        random.seed(42)  # Control randomness

        resolver = CombatResolver()
        character = {
            "name": "Test Fighter",
            "hp": 10,
            "stats": {"strength": 16, "dexterity": 12}
        }
        enemy = CombatEnemy(
            id="test",
            name="Weak Goblin",
            hp=1,
            max_hp=1,
            ac=10,  # Easy to hit
            attack_bonus=0,
            damage_dice="1d4",
            xp_value=10,
        )

        result = resolver.resolve_player_attack(character, enemy)

        # With seed 42 and these stats, verify expected outcome
        assert result.is_hit == True  # or check based on known seed
        if result.is_hit:
            assert result.target_dead == True

    def test_player_death(self):
        """Player should die when HP reaches 0."""
        random.seed(123)  # Seed that produces enemy hits

        resolver = CombatResolver()
        character = {
            "name": "Fragile Wizard",
            "hp": 3,  # Low HP
            "stats": {"strength": 8, "dexterity": 10}
        }
        enemy = CombatEnemy(
            id="test",
            name="Orc",
            hp=10,
            max_hp=10,
            ac=13,
            attack_bonus=5,  # High bonus
            damage_dice="1d8+2",  # High damage
            xp_value=25,
        )

        result = resolver.resolve_enemy_attack(enemy, character)

        if result.is_hit and result.damage >= 3:
            assert result.target_dead == True
```

**Validation**:
- [ ] All test files pass
- [ ] Coverage >= 80%
- [ ] Edge cases covered

---

## Testing Requirements

### Unit Tests

| Test Case | Description |
|-----------|-------------|
| `test_dice_roll_basic` | Roll "1d20" returns 1-20 |
| `test_dice_roll_modifier` | Roll "2d6+3" includes modifier |
| `test_dice_roll_negative_modifier` | Roll "1d8-1" handles negative |
| `test_dice_roll_invalid` | Invalid notation raises ValueError |
| `test_spawn_goblin` | Goblin spawns with correct stats |
| `test_spawn_unknown` | Unknown enemy raises ValueError |
| `test_player_attack_hit` | Hit deals damage to enemy |
| `test_player_attack_miss` | Miss deals no damage |
| `test_player_attack_crit` | Natural 20 always hits |
| `test_player_attack_fumble` | Natural 1 always misses |
| `test_enemy_attack_kills_player` | Player dies at 0 HP |
| `test_combat_round_player_first` | Higher initiative attacks first |
| `test_combat_round_enemy_first` | Lower initiative attacks second |
| `test_combat_ends_all_dead` | Combat ends when all enemies dead |
| `test_combat_ends_player_dead` | Combat ends when player dead |
| `test_xp_awarded_on_kill` | XP granted when enemy dies |

### Integration Tests

| Scenario | Description |
|----------|-------------|
| Full combat round with mocked random | Verify complete round flow |
| Combat initiation from Claude response | Verify enemy spawning |
| Character death ends session | Verify session status update |
| XP accumulates correctly | Verify character XP after combat |

### Manual Testing

1. Create character, start session, enter combat area
2. Attack enemy, verify dice rolls shown in UI
3. Take damage, verify HP decreases
4. Kill enemy, verify XP gained
5. Let character die, verify session ends
6. Try action after death, verify error message

---

## Integration Test Plan

### Prerequisites
- Backend deployed: `cd cdk && cdk deploy --all`
- Frontend running: `cd frontend && npm run dev`
- Browser DevTools open (Console + Network tabs)

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Create a low-HP magic-user (should have ~4 HP) | Character created | ☐ |
| 2 | Start session, explore until combat | Combat begins, initiative rolled | ☐ |
| 3 | Attack enemy | Server rolls attack, damage applied | ☐ |
| 4 | Take hit from enemy | Player HP decreases by rolled amount | ☐ |
| 5 | Repeat until enemy or player dies | Death triggers correctly | ☐ |
| 6 | If player died, verify session ended | Session status = "ended" | ☐ |
| 7 | Try to take action in ended session | Error: "Session has ended" | ☐ |

### Death Test (Critical)
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Player death | Fight vampire at level 1 | Character dies, session ends | ☐ |
| Enemy death | Fight goblin | Goblin dies, XP awarded | ☐ |
| Natural 1 | Keep attacking until fumble | Attack misses regardless of AC | ☐ |
| Natural 20 | Keep attacking until crit | Attack hits regardless of AC | ☐ |

### Browser Checks
- [ ] No CORS errors in Console
- [ ] No JavaScript errors in Console
- [ ] Combat API requests visible in Network tab
- [ ] Dice rolls visible in response data
- [ ] HP changes match rolled damage

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| `ValueError("Invalid dice notation")` | Malformed dice string | Log warning, use default 1d6 |
| `ValueError("Unknown enemy type")` | Enemy not in bestiary | Use Claude-provided stats as fallback |
| `GameStateError("Session has ended")` | Action after death | Return 400, "character_death" reason |

### Edge Cases
- **Multiple enemies**: Attack first living enemy, all enemies attack
- **Zero enemies**: Combat shouldn't start with no enemies
- **Negative modifier**: STR 3 gives -3, damage can't go below 1
- **High AC enemy**: Low-level player should still be able to crit
- **Flee attempt**: Out of scope for this PRP (future feature)

---

## Cost Impact

### Claude API
- Combat prompts slightly larger (~300 extra tokens for outcome block)
- But Claude makes FEWER decisions (just narration)
- Estimated: **No significant change** to per-action cost

### AWS
- Slightly more computation in Lambda for dice rolling
- Negligible impact on Lambda execution time
- No new AWS resources
- Estimated: **$0 additional monthly cost**

---

## Open Questions

1. ~~**Combat detection method?**~~ Resolved: Use combat_state.active flag
2. **Should players be able to flee?** Deferred to future PRP
3. **Multiple attacks per round for high-level fighters?** Deferred (levels 15+)
4. **Spell combat resolution?** Deferred to init-10 or later
5. **Should random seed be logged for replay/debugging?** Nice to have, not required for MVP

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Clear problem, clear solution, detailed spec |
| Feasibility | 9 | Uses existing patterns, straightforward implementation |
| Completeness | 8 | Core combat covered, some features deferred |
| Alignment | 10 | Directly addresses permadeath requirement, fits budget |
| **Overall** | **9** | High confidence - well-defined, achievable |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
- [x] Integration test plan defined
- [x] Edge cases documented
