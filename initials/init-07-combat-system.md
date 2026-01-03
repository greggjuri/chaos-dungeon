# init-09-combat-system

## Overview

Implement server-side dice rolling and combat resolution to ensure fair, mechanical outcomes. Currently, Claude adjudicates combat and consistently fudges rolls in the player's favor, making character death impossible. This defeats the core design of a permadeath roguelike.

**The fix**: The server rolls all dice, calculates hits/misses/damage, applies state changes, then tells Claude what happened. Claude only narrates predetermined outcomes — it cannot fudge.

## Problem Statement

Current behavior:
1. Player says "I attack the goblin"
2. Claude decides the outcome (always favorable to player)
3. Player never dies, game has no stakes

Desired behavior:
1. Player says "I attack the goblin"
2. Server rolls d20 + modifiers vs AC
3. Server calculates damage if hit
4. Server applies HP changes
5. Server checks for death
6. Claude narrates the mechanical outcome it's given

## Dependencies

- init-06-action-handler (Current action flow)
- init-05-dm-system-prompt (Prompt structure)
- BECMI rules (already defined in prompts/rules.py)

## Combat Flow

```
┌─────────────────┐
│  Player Action  │
│ "I attack the   │
│    goblin"      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Combat Detector │
│ Is this combat? │
└────────┬────────┘
         │ Yes
         ▼
┌─────────────────┐
│  Server Rolls   │
│ d20 + STR mod   │
│ vs enemy AC     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Calculate Hit?  │
│ Roll ≥ AC = HIT │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
   HIT       MISS
    │         │
    ▼         │
┌─────────┐   │
│ Roll    │   │
│ Damage  │   │
└────┬────┘   │
     │        │
     ▼        │
┌─────────────┴───┐
│ Enemy Turn      │
│ (same process)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Apply Damage    │
│ Check for Death │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Build Outcome   │
│ for Claude      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Claude Narrates │
│ (cannot change  │
│  the outcome)   │
└─────────────────┘
```

## Combat State Model

Add combat tracking to session:

```python
class CombatState(BaseModel):
    """Active combat encounter."""
    active: bool = False
    round: int = 0
    player_initiative: int = 0
    enemy_initiative: int = 0
    enemies: list[Enemy] = []

class Enemy(BaseModel):
    """Enemy in combat."""
    id: str  # uuid for tracking
    name: str
    hp: int
    max_hp: int
    ac: int
    attack_bonus: int = 0
    damage_dice: str = "1d6"  # e.g., "1d6", "2d4+1"
    xp_value: int = 10
```

## Dice Rolling Module

```python
# lambdas/shared/dice.py

import random
import re

def roll(notation: str) -> tuple[int, list[int]]:
    """Roll dice using standard notation.
    
    Args:
        notation: Dice notation like "1d20", "2d6+3", "1d8-1"
    
    Returns:
        (total, individual_rolls)
    
    Examples:
        roll("1d20") -> (15, [15])
        roll("2d6+3") -> (11, [4, 4])  # 4+4+3
        roll("1d8-1") -> (5, [6])  # 6-1
    """
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


def roll_attack(attack_bonus: int) -> tuple[int, int]:
    """Roll a d20 attack.
    
    Returns:
        (total, natural_roll)
    """
    natural = random.randint(1, 20)
    return natural + attack_bonus, natural


def roll_initiative() -> int:
    """Roll d6 for initiative."""
    return random.randint(1, 6)
```

## Combat Resolution Service

```python
# lambdas/dm/combat.py

class CombatResolver:
    """Handles server-side combat resolution."""
    
    def resolve_player_attack(
        self,
        character: dict,
        target: Enemy,
        weapon: str = "melee"
    ) -> AttackResult:
        """Resolve player attacking an enemy."""
        # Calculate attack bonus
        if weapon == "melee":
            stat_mod = calculate_modifier(character["stats"]["strength"])
        else:
            stat_mod = calculate_modifier(character["stats"]["dexterity"])
        
        attack_bonus = stat_mod  # + level bonuses later
        
        # Roll attack
        total, natural = roll_attack(attack_bonus)
        is_hit = total >= target.ac
        is_crit = natural == 20
        is_fumble = natural == 1
        
        damage = 0
        damage_rolls = []
        
        if is_hit and not is_fumble:
            # Roll damage (weapon die + STR for melee)
            damage, damage_rolls = roll(self._get_weapon_damage(character))
            damage = max(1, damage + stat_mod)  # Minimum 1 damage
            
            # Apply damage to enemy
            target.hp -= damage
        
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
            target_hp_before=target.hp + damage,
            target_hp_after=target.hp,
            target_dead=target.hp <= 0,
        )
    
    def resolve_enemy_attack(
        self,
        enemy: Enemy,
        character: dict,
    ) -> AttackResult:
        """Resolve enemy attacking player."""
        # Calculate player AC
        player_ac = self._calculate_ac(character)
        
        # Roll attack
        total, natural = roll_attack(enemy.attack_bonus)
        is_hit = total >= player_ac
        is_crit = natural == 20
        is_fumble = natural == 1
        
        damage = 0
        damage_rolls = []
        
        if is_hit and not is_fumble:
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
            target_hp_before=character["hp"],
            target_hp_after=character["hp"] - damage if is_hit else character["hp"],
            target_dead=(character["hp"] - damage) <= 0 if is_hit else False,
        )
    
    def resolve_combat_round(
        self,
        character: dict,
        combat_state: CombatState,
        player_action: str,
    ) -> CombatRoundResult:
        """Resolve a full combat round.
        
        BECMI: Each side acts once per round based on initiative.
        """
        results = []
        xp_gained = 0
        
        # Determine who goes first (re-roll each round or keep initial?)
        player_first = combat_state.player_initiative >= combat_state.enemy_initiative
        
        if player_first:
            # Player attacks first
            for enemy in combat_state.enemies:
                if enemy.hp > 0:
                    result = self.resolve_player_attack(character, enemy)
                    results.append(result)
                    if result.target_dead:
                        xp_gained += enemy.xp_value
                    break  # One attack per round at level 1
            
            # Surviving enemies counterattack
            for enemy in combat_state.enemies:
                if enemy.hp > 0:
                    result = self.resolve_enemy_attack(enemy, character)
                    results.append(result)
                    if result.is_hit:
                        character["hp"] -= result.damage
        else:
            # Enemies attack first
            for enemy in combat_state.enemies:
                if enemy.hp > 0:
                    result = self.resolve_enemy_attack(enemy, character)
                    results.append(result)
                    if result.is_hit:
                        character["hp"] -= result.damage
            
            # Player counterattacks if alive
            if character["hp"] > 0:
                for enemy in combat_state.enemies:
                    if enemy.hp > 0:
                        result = self.resolve_player_attack(character, enemy)
                        results.append(result)
                        if result.target_dead:
                            xp_gained += enemy.xp_value
                        break
        
        # Check combat end conditions
        all_enemies_dead = all(e.hp <= 0 for e in combat_state.enemies)
        player_dead = character["hp"] <= 0
        
        return CombatRoundResult(
            round=combat_state.round,
            attack_results=results,
            player_hp=character["hp"],
            player_dead=player_dead,
            enemies_remaining=[e for e in combat_state.enemies if e.hp > 0],
            combat_ended=all_enemies_dead or player_dead,
            xp_gained=xp_gained,
        )
```

## Result Models

```python
# lambdas/dm/models.py (additions)

class AttackResult(BaseModel):
    """Result of a single attack."""
    attacker: str
    defender: str
    attack_roll: int  # Natural d20 roll
    attack_bonus: int
    attack_total: int
    target_ac: int
    is_hit: bool
    is_critical: bool = False
    is_fumble: bool = False
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
    enemies_remaining: list[Enemy]
    combat_ended: bool
    xp_gained: int = 0
```

## Updated Prompt Format

Tell Claude the outcome, don't ask it to decide:

```python
COMBAT_OUTCOME_PROMPT = """
## COMBAT OUTCOME (NARRATE THIS EXACTLY)

The following combat has been mechanically resolved. Your job is ONLY to narrate
what happened in dramatic fashion. You CANNOT change the outcome.

Round {round}:

{attack_summaries}

FINAL STATE:
- Player HP: {player_hp}/{player_max_hp}
- Player Status: {player_status}
- Enemies: {enemy_status}

Narrate this combat round with vivid detail. If the player died, describe their
death dramatically. Do not soften or change the outcome.
"""
```

Example outcome sent to Claude:

```
## COMBAT OUTCOME (NARRATE THIS EXACTLY)

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

Narrate this combat round with vivid detail.
```

## Enemy Bestiary (Basic)

```python
# lambdas/dm/bestiary.py

BESTIARY = {
    "goblin": {
        "name": "Goblin",
        "hp_dice": "1d6",
        "ac": 12,
        "attack_bonus": 1,
        "damage_dice": "1d6",
        "xp_value": 10,
    },
    "skeleton": {
        "name": "Skeleton",
        "hp_dice": "1d8",
        "ac": 13,
        "attack_bonus": 1,
        "damage_dice": "1d6",
        "xp_value": 15,
    },
    "orc": {
        "name": "Orc",
        "hp_dice": "1d8+1",
        "ac": 13,
        "attack_bonus": 2,
        "damage_dice": "1d8",
        "xp_value": 25,
    },
    "zombie": {
        "name": "Zombie",
        "hp_dice": "2d8",
        "ac": 11,
        "attack_bonus": 1,
        "damage_dice": "1d8",
        "xp_value": 20,
    },
    "wolf": {
        "name": "Wolf",
        "hp_dice": "2d6",
        "ac": 13,
        "attack_bonus": 2,
        "damage_dice": "1d6",
        "xp_value": 25,
    },
    "giant_spider": {
        "name": "Giant Spider",
        "hp_dice": "2d8",
        "ac": 13,
        "attack_bonus": 2,
        "damage_dice": "1d6",  # + poison save
        "xp_value": 50,
    },
    "vampire": {
        "name": "Vampire",
        "hp_dice": "8d8",
        "ac": 18,
        "attack_bonus": 8,
        "damage_dice": "1d10+4",
        "xp_value": 1000,
    },
}

def spawn_enemy(enemy_type: str) -> Enemy:
    """Create an enemy instance with rolled HP."""
    template = BESTIARY.get(enemy_type.lower())
    if not template:
        raise ValueError(f"Unknown enemy type: {enemy_type}")
    
    hp, _ = roll(template["hp_dice"])
    
    return Enemy(
        id=str(uuid.uuid4()),
        name=template["name"],
        hp=hp,
        max_hp=hp,
        ac=template["ac"],
        attack_bonus=template["attack_bonus"],
        damage_dice=template["damage_dice"],
        xp_value=template["xp_value"],
    )
```

## Combat Detection

How does the server know when to trigger combat resolution?

Option A: **Keyword detection** (simple but fragile)
```python
COMBAT_KEYWORDS = ["attack", "strike", "hit", "fight", "kill", "stab", "slash"]
```

Option B: **Claude decides, server executes** (hybrid)
1. Claude responds with intent: `{"action_type": "combat", "target": "goblin"}`
2. Server resolves mechanically
3. Claude narrates outcome

Option C: **Always in combat mode when enemies present**
- If `session.combat_state.active == True`, all actions are combat
- Player must explicitly flee/disengage to exit combat

**Recommendation**: Option C — clearest, least ambiguous.

## Combat Initiation

When does combat start?

1. **Claude-initiated**: Claude's response includes enemies
2. **Server validates**: Check if enemies are in bestiary
3. **Roll initiative**: Server rolls d6 for each side
4. **Set combat state**: `session.combat_state.active = True`

```python
def initiate_combat(session: dict, enemies: list[str]) -> CombatState:
    """Start combat with given enemy types."""
    spawned = [spawn_enemy(e) for e in enemies]
    
    return CombatState(
        active=True,
        round=1,
        player_initiative=roll_initiative(),
        enemy_initiative=roll_initiative(),
        enemies=spawned,
    )
```

## File Structure

```
lambdas/
├── shared/
│   └── dice.py              # NEW: Dice rolling utilities
├── dm/
│   ├── combat.py            # NEW: Combat resolution
│   ├── bestiary.py          # NEW: Enemy definitions
│   ├── service.py           # MODIFY: Integrate combat
│   └── prompts/
│       └── combat_prompt.py # NEW: Combat narration prompts
├── tests/
│   ├── test_dice.py         # NEW: Dice tests
│   ├── test_combat.py       # NEW: Combat tests
│   └── test_bestiary.py     # NEW: Bestiary tests
```

## Acceptance Criteria

- [ ] Dice rolls happen server-side with Python random
- [ ] Attack resolution uses BECMI rules (d20 + mod vs AC)
- [ ] Damage is rolled server-side
- [ ] Claude receives outcomes, not choices
- [ ] Character HP updates reflect actual damage taken
- [ ] Character death occurs when HP ≤ 0
- [ ] Enemy death occurs when HP ≤ 0 and awards XP
- [ ] Combat state persists in session
- [ ] Initiative determines attack order
- [ ] Unit tests for dice rolling (distribution sanity check)
- [ ] Unit tests for combat resolution
- [ ] Integration test: combat round with mocked random

## Testing Strategy

### Deterministic Tests

Seed `random` for reproducible tests:

```python
def test_combat_player_dies():
    random.seed(42)  # Known seed that produces bad rolls
    
    character = {"hp": 3, "stats": {"strength": 10, ...}}
    enemy = spawn_enemy("orc")
    
    result = resolver.resolve_enemy_attack(enemy, character)
    
    # With seed 42, we know the exact outcome
    assert result.is_hit == True
    assert result.damage == 6
    assert result.target_dead == True
```

### Manual Death Test

After implementation, test character death:

```bash
# Create fragile magic-user
# Enter combat with orc (1d8 damage)
# With 3 HP, one good hit kills
# Verify session.status == "ended"
```

## Migration Notes

Existing sessions with `enemies` in `world_state` may have old format. Add migration or handle both:

```python
# Handle both old (Claude-defined) and new (server-spawned) enemy formats
if "enemies" in session and isinstance(session["enemies"][0], dict):
    if "id" not in session["enemies"][0]:
        # Old format, migrate
        session["combat_state"] = migrate_legacy_combat(session)
```

## Out of Scope

- Fleeing/retreat mechanics (future)
- Multiple attacks per round (Fighter level 15+)
- Spell combat resolution (init-10 or later)
- Special abilities (backstab, turn undead)
- Saving throws in combat (poison, etc.)
- Morale checks for enemies

## Notes

- This fundamentally changes the trust model: Claude narrates, server decides
- May need to update prompt caching since combat prompts differ
- Consider adding "DM override" for narrative-only sessions later
- Random seed logging for debugging/replay
