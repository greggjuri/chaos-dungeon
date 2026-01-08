# init-12-turn-based-combat

## Overview

Implement proper turn-based combat where the server controls combat flow, players choose actions each round, and the AI only narrates predetermined outcomes. Currently, combat resolves in a single AI response with arbitrary results. This breaks immersion and removes player agency.

## Dependencies

- init-09-mistral-dm (AI narration working)
- init-10-cost-protection (token limits in place)
- Server-side dice rolling (already implemented per ADR-008)

## Goals

1. **Turn-based rounds** — Combat proceeds in initiative order, one turn at a time
2. **Player agency** — Player chooses action each round (attack, defend, flee, use item, cast spell)
3. **Server authority** — All dice rolls and damage calculated server-side
4. **AI narrates only** — AI describes outcomes of predetermined mechanical results
5. **Clear combat UI** — Player sees enemy HP, their options, and combat log
6. **Proper BECMI rules** — Initiative, THAC0/AC, damage dice per weapon/monster

## Current Problems

From production testing:

```
You: I kill him.
DM: [Narrates entire combat in one response]
    - AI decided outcome without player input
    - Multiple rounds resolved at once
    - Dice shown but didn't drive narrative
    - HP loss arbitrary
```

## Target Experience

```
[Combat Initiated: 3 Goblins]

Round 1 - Your Turn
Enemies: Goblin A (HP: 4/4), Goblin B (HP: 4/4), Goblin C (HP: 4/4)
Your HP: 8/8

What do you do?
> [Attack Goblin A] [Defend] [Flee] [Use Item]

Player clicks: Attack Goblin A

Server rolls: d20(14) + 1 = 15 vs AC 6 → HIT
Server rolls: d8(5) + 1 = 6 damage → Goblin A DEAD

DM: "Your sword cuts through the air in a deadly arc, 
     catching the goblin square in the chest. It crumples 
     to the ground with a gurgling shriek."

Round 1 - Enemy Turn
Goblin B attacks you: d20(8) vs AC 7 → MISS
Goblin C attacks you: d20(17) vs AC 7 → HIT, 1d6(3) = 3 damage

DM: "The remaining goblins screech in fury. One lunges 
     wildly, its rusty blade whistling past your ear. 
     The other finds its mark, slicing across your arm."

Your HP: 5/8

Round 2 - Your Turn
...
```

## Combat State Machine

```
┌─────────────────┐
│  EXPLORATION    │ (normal gameplay)
└────────┬────────┘
         │ Combat triggered
         ▼
┌─────────────────┐
│ COMBAT_START    │ Roll initiative, set up enemies
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PLAYER_TURN     │◄─────────────────────┐
│                 │                       │
│ Awaiting action │                       │
└────────┬────────┘                       │
         │ Player submits action          │
         ▼                                │
┌─────────────────┐                       │
│ RESOLVE_PLAYER  │ Server rolls dice,    │
│                 │ applies damage,       │
│                 │ AI narrates result    │
└────────┬────────┘                       │
         │                                │
         ▼                                │
┌─────────────────┐                       │
│ CHECK_ENEMIES   │ All dead? ───────────►│ COMBAT_END (victory)
└────────┬────────┘                       │
         │ Enemies remain                 │
         ▼                                │
┌─────────────────┐                       │
│ ENEMY_TURN      │ Server rolls for each │
│                 │ enemy, AI narrates    │
└────────┬────────┘                       │
         │                                │
         ▼                                │
┌─────────────────┐                       │
│ CHECK_PLAYER    │ Player dead? ────────►│ COMBAT_END (death)
└────────┬────────┘                       │
         │ Player alive                   │
         └────────────────────────────────┘

┌─────────────────┐
│  COMBAT_END     │ Award XP/loot, return to exploration
└─────────────────┘
```

## Data Models

### CombatState (stored in Session)

```python
class EnemyInstance(BaseModel):
    """Single enemy in combat."""
    id: str                    # "goblin_a"
    name: str                  # "Goblin"
    display_name: str          # "Goblin A"
    hp: int                    # Current HP
    max_hp: int                # Maximum HP
    ac: int                    # Armor class
    thac0: int                 # To-hit AC 0 (BECMI)
    attacks: list[Attack]      # Available attacks
    xp_value: int              # XP awarded on kill
    is_dead: bool = False


class Attack(BaseModel):
    """Enemy attack definition."""
    name: str                  # "Claw" or "Bite"
    damage_dice: str           # "1d6" or "2d4+1"
    bonus: int = 0             # Attack bonus


class CombatState(BaseModel):
    """Active combat state."""
    active: bool = False
    round: int = 1
    phase: CombatPhase         # PLAYER_TURN, ENEMY_TURN, etc.
    enemies: list[EnemyInstance]
    initiative_order: list[str]  # IDs in turn order
    current_turn: str          # ID of whose turn it is
    combat_log: list[CombatLogEntry]
    

class CombatPhase(str, Enum):
    COMBAT_START = "combat_start"
    PLAYER_TURN = "player_turn"
    RESOLVE_PLAYER = "resolve_player"
    ENEMY_TURN = "enemy_turn"
    COMBAT_END = "combat_end"


class CombatLogEntry(BaseModel):
    """Single entry in combat log."""
    round: int
    actor: str                 # "player" or enemy ID
    action: str                # "attack", "defend", "flee"
    target: str | None
    roll: DiceRoll | None
    damage: int | None
    result: str                # "hit", "miss", "killed", "fled"
    narrative: str             # AI-generated description
```

### Combat Actions (Player Input)

```python
class CombatAction(BaseModel):
    """Player's chosen combat action."""
    action_type: CombatActionType
    target_id: str | None = None  # For attack actions
    item_id: str | None = None    # For use item actions
    spell_id: str | None = None   # For cast spell actions


class CombatActionType(str, Enum):
    ATTACK = "attack"
    DEFEND = "defend"          # +2 AC this round
    FLEE = "flee"              # Dex check to escape
    USE_ITEM = "use_item"      # Potion, etc.
    CAST_SPELL = "cast_spell"  # If Magic-User/Cleric
```

## API Changes

### Modified: POST /sessions/{id}/action

When in combat, the action endpoint behavior changes:

```python
# Request body during combat
{
    "action": "attack goblin_a"  # Free text still works
    # OR structured combat action:
    "combat_action": {
        "action_type": "attack",
        "target_id": "goblin_a"
    }
}

# Response during combat
{
    "narrative": "Your sword finds its mark...",
    "combat": {
        "active": true,
        "round": 1,
        "phase": "player_turn",
        "your_hp": 5,
        "your_max_hp": 8,
        "enemies": [
            {"id": "goblin_a", "name": "Goblin A", "hp": 0, "max_hp": 4, "is_dead": true},
            {"id": "goblin_b", "name": "Goblin B", "hp": 4, "max_hp": 4, "is_dead": false}
        ],
        "available_actions": ["attack", "defend", "flee", "use_item"],
        "valid_targets": ["goblin_b"],
        "combat_log": [
            {
                "round": 1,
                "actor": "player",
                "action": "attack",
                "target": "goblin_a",
                "roll": {"type": "attack", "dice": "d20", "roll": 14, "modifier": 1, "total": 15},
                "damage": 6,
                "result": "killed",
                "narrative": "Your sword finds its mark..."
            }
        ]
    },
    "state_changes": {
        "hp_delta": -3,
        "xp_delta": 25
    }
}
```

## Implementation Steps

### Step 1: Create Combat Models

Create `lambdas/shared/combat_models.py`:
- EnemyInstance, Attack, CombatState, CombatPhase
- CombatAction, CombatActionType
- CombatLogEntry

### Step 2: Create Enemy Definitions

Create `lambdas/dm/enemies.py`:
- Monster stat blocks (goblin, orc, skeleton, etc.)
- Factory function to spawn enemy instances
- BECMI-accurate stats (HD, AC, damage, XP value)

```python
ENEMY_TEMPLATES = {
    "goblin": {
        "name": "Goblin",
        "hd": "1d8-1",        # Hit dice
        "ac": 6,
        "thac0": 19,
        "attacks": [{"name": "Short sword", "damage": "1d6"}],
        "xp_value": 5,
    },
    "orc": {
        "name": "Orc", 
        "hd": "1d8",
        "ac": 6,
        "thac0": 19,
        "attacks": [{"name": "Battle axe", "damage": "1d8"}],
        "xp_value": 10,
    },
    # ... more enemies
}
```

### Step 3: Create Combat Engine

Create `lambdas/dm/combat_engine.py`:
- `initiate_combat(enemies: list[str]) -> CombatState`
- `roll_initiative(player_dex: int, enemies: list) -> list[str]`
- `resolve_player_attack(player, target, weapon) -> AttackResult`
- `resolve_enemy_turn(enemy, player) -> AttackResult`
- `check_combat_end(combat_state) -> CombatEndReason | None`
- `calculate_rewards(defeated_enemies) -> Rewards`

All dice rolls use existing `roll_dice()` function (server-side).

### Step 4: Create Combat Narrator

Create `lambdas/dm/combat_narrator.py`:
- Takes mechanical results (hit/miss/damage/kill)
- Calls AI to generate narrative description
- Prompt focuses on describing the outcome, not deciding it

```python
COMBAT_NARRATOR_PROMPT = """
You are narrating combat in a dark fantasy RPG.
Describe ONLY the outcome provided. Do not add extra attacks or change results.

Mechanical Result:
- Attacker: {attacker}
- Target: {target}  
- Action: {action}
- Roll: {roll} vs AC {ac} = {hit_or_miss}
- Damage: {damage} (target now at {target_hp} HP)
- Result: {result}

Write 1-2 sentences describing this moment dramatically.
Do NOT include dice numbers in the narrative.
"""
```

### Step 5: Update Action Handler

Modify `lambdas/dm/handler.py`:
- Detect if session is in combat
- Route to combat handler vs exploration handler
- Parse combat actions from free text ("attack the goblin" → attack action)

```python
def handle_action(session, action_text, combat_action=None):
    if session.combat_state and session.combat_state.active:
        return handle_combat_action(session, action_text, combat_action)
    else:
        return handle_exploration_action(session, action_text)
```

### Step 6: Combat Action Parser

Create `lambdas/dm/combat_parser.py`:
- Parse free text into structured combat actions
- "attack goblin" → CombatAction(type=ATTACK, target="goblin_a")
- "run away" → CombatAction(type=FLEE)
- "drink potion" → CombatAction(type=USE_ITEM, item="health_potion")

### Step 7: Update Session Model

Modify `lambdas/shared/models.py`:
- Add `combat_state: CombatState | None` to Session
- Update session serialization/deserialization

### Step 8: Frontend Combat UI

Create `frontend/src/components/game/CombatUI.tsx`:
- Enemy list with HP bars
- Action buttons (Attack, Defend, Flee, Items)
- Target selection when attacking
- Combat log showing recent actions
- Clear visual distinction from exploration mode

```typescript
interface CombatUIProps {
    combat: CombatState;
    onAction: (action: CombatAction) => void;
}

function CombatUI({ combat, onAction }: CombatUIProps) {
    return (
        <div className="combat-ui">
            <EnemyList enemies={combat.enemies} />
            <PlayerStatus hp={combat.your_hp} maxHp={combat.your_max_hp} />
            <ActionBar 
                actions={combat.available_actions}
                targets={combat.valid_targets}
                onAction={onAction}
            />
            <CombatLog entries={combat.combat_log} />
        </div>
    );
}
```

### Step 9: Update Game Page

Modify `frontend/src/pages/GamePage.tsx`:
- Detect combat state in response
- Show CombatUI when in combat
- Hide regular action input during combat (use action buttons instead)

### Step 10: Combat Initiation

Modify AI prompt to output structured combat initiation:

```python
# When AI detects combat should start, it outputs:
{
    "narrative": "The goblins leap from the shadows...",
    "initiate_combat": {
        "enemies": ["goblin", "goblin", "goblin"],
        "surprise": false
    }
}
```

Server then:
1. Spawns enemy instances from templates
2. Rolls initiative
3. Sets combat_state.active = True
4. Returns first turn prompt to player

## BECMI Combat Rules Reference

### Initiative
- Each side rolls 1d6 at start of combat
- Higher roll acts first
- Re-roll each round (optional, can simplify to roll once)

### Attack Roll
- Roll d20 + modifiers
- Compare to target's AC (BECMI uses descending AC, we convert to ascending)
- THAC0 system: Need to roll (THAC0 - target AC) or higher

### Damage
- Weapon damage dice + STR modifier (melee) or DEX modifier (ranged)
- Fighter: d8 (sword), d6 (short sword), d4 (dagger)
- Monsters: As defined in stat block

### Death
- 0 HP = dead (BECMI is harsh)
- Optional: -10 HP rule for player characters (bleeding out)

## Testing Plan

### Unit Tests
- Combat engine: initiative, attack resolution, damage calculation
- Combat parser: free text to structured actions
- Enemy spawning from templates
- Combat state transitions

### Integration Tests
- Full combat flow: initiate → player turn → enemy turn → end
- Combat persists across API calls
- XP/gold awarded on victory
- Death triggers correctly

### Manual Tests
1. Start combat with multiple enemies
2. Kill one enemy, verify others remain
3. Take damage, verify HP updates
4. Flee successfully
5. Die in combat, verify death screen
6. Use item during combat
7. Cast spell during combat (if Magic-User)

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `lambdas/shared/combat_models.py` | CREATE | Combat data models |
| `lambdas/dm/enemies.py` | CREATE | Enemy templates and spawning |
| `lambdas/dm/combat_engine.py` | CREATE | Combat resolution logic |
| `lambdas/dm/combat_narrator.py` | CREATE | AI narration for combat |
| `lambdas/dm/combat_parser.py` | CREATE | Parse free text to actions |
| `lambdas/dm/handler.py` | MODIFY | Route combat vs exploration |
| `lambdas/dm/service.py` | MODIFY | Integrate combat engine |
| `lambdas/shared/models.py` | MODIFY | Add combat_state to Session |
| `frontend/src/components/game/CombatUI.tsx` | CREATE | Combat interface |
| `frontend/src/components/game/EnemyList.tsx` | CREATE | Enemy HP display |
| `frontend/src/components/game/ActionBar.tsx` | CREATE | Combat action buttons |
| `frontend/src/components/game/CombatLog.tsx` | CREATE | Combat history |
| `frontend/src/pages/GamePage.tsx` | MODIFY | Integrate combat UI |
| `frontend/src/types/index.ts` | MODIFY | Combat types |
| `lambdas/tests/test_combat_engine.py` | CREATE | Combat unit tests |
| `lambdas/tests/test_combat_parser.py` | CREATE | Parser unit tests |

## Acceptance Criteria

- [ ] Combat proceeds turn-by-turn, not all at once
- [ ] Player chooses action each round via UI buttons
- [ ] Server rolls all dice, AI only narrates outcomes
- [ ] Enemy HP visible and updates correctly
- [ ] Player can attack specific targets
- [ ] Player can defend (+2 AC) or flee
- [ ] Combat ends when all enemies dead (victory)
- [ ] Combat ends when player reaches 0 HP (death)
- [ ] XP awarded for defeated enemies
- [ ] Combat state persists if player refreshes page
- [ ] Free text input still works ("attack goblin")
- [ ] BECMI-accurate to-hit and damage calculations

## Out of Scope

- Spellcasting system (separate init)
- Multiple player characters / party
- Enemy AI tactics (flanking, focus fire)
- Retreat/chase mechanics
- Combat grid / positioning
- Status effects (poison, paralysis)
- Morale checks for enemies

## Cost Impact

Combat will require more AI calls (one per turn for narration), but each call is small (1-2 sentences). Estimated:
- Current: 1 large call per combat (~800 tokens)
- New: 4-8 small calls per combat (~200 tokens each = 800-1600 tokens)

Slight increase but within budget. Combat narration prompts will be minimal.

## Notes

- Keep exploration AI calls unchanged - combat is a separate code path
- Combat narrator uses smaller, focused prompts
- State machine prevents AI from "deciding" combat outcomes
- Player can still type free text, but buttons are primary UI during combat
