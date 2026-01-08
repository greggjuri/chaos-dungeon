# PRP-012: Turn-Based Combat

**Created**: 2026-01-08
**Initial**: `initials/init-12-turn-based-combat.md`
**Status**: Ready

---

## Overview

### Problem Statement

Currently, combat resolves in a single AI response with arbitrary results. The player types "I kill him" and the DM narrates the entire combat in one message, deciding outcomes without player input. This breaks immersion and removes player agency - the core appeal of a turn-based RPG.

From production testing:
```
Player: I kill him.
DM: [Narrates entire combat in one response]
    - Multiple rounds resolved at once
    - Dice shown but didn't drive narrative
    - HP loss arbitrary
```

### Proposed Solution

Implement proper turn-based combat where:
1. Combat proceeds in initiative order, one turn at a time
2. Player chooses action each round via UI buttons (attack, defend, flee, use item)
3. Server rolls all dice and calculates damage
4. AI only narrates the predetermined mechanical outcomes
5. Combat state persists across API calls

### Success Criteria

- [ ] Combat proceeds turn-by-turn, not all at once
- [ ] Player chooses action each round via UI buttons
- [ ] Server rolls all dice, AI only narrates outcomes
- [ ] Enemy HP visible and updates correctly
- [ ] Player can attack specific targets
- [ ] Player can defend (+2 AC) or flee (Dex check)
- [ ] Combat ends when all enemies dead (victory) or player at 0 HP (death)
- [ ] XP awarded for defeated enemies
- [ ] Combat state persists if player refreshes page
- [ ] Free text input still works ("attack goblin")
- [ ] BECMI-accurate to-hit and damage calculations

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Architecture overview, BECMI rules reference
- `docs/DECISIONS.md` - ADR-009 (Mistral), ADR-010 (Cost Protection)
- `initials/init-12-turn-based-combat.md` - Full specification

### Dependencies

- **Required**:
  - init-09-mistral-dm (AI narration working) - COMPLETE
  - init-10-cost-protection (token limits in place) - COMPLETE
  - Server-side dice rolling (already in `lambdas/shared/dice.py`)
  - Combat resolver (already in `lambdas/dm/combat.py`)

- **Existing Foundation**:
  - `CombatState`, `CombatEnemy`, `AttackResult` models exist
  - `CombatResolver.resolve_combat_round()` exists
  - `bestiary.py` with 7 enemy types exists
  - `CombatStatus` frontend component exists

### Files to Modify/Create

```
# NEW FILES
lambdas/dm/combat_narrator.py      # AI-only narration for combat outcomes
lambdas/dm/combat_parser.py        # Parse free text to combat actions
lambdas/shared/combat_actions.py   # Player combat action models
frontend/src/components/game/CombatUI.tsx      # Main combat interface
frontend/src/components/game/ActionBar.tsx     # Combat action buttons
frontend/src/components/game/CombatLog.tsx     # Combat history display
frontend/src/components/game/EnemyCard.tsx     # Individual enemy display

# MODIFIED FILES
lambdas/dm/models.py               # Add CombatPhase, CombatAction models
lambdas/dm/combat.py               # Refactor for turn-by-turn resolution
lambdas/dm/service.py              # Route combat vs exploration, phase handling
lambdas/dm/handler.py              # Parse combat_action from request
lambdas/shared/models.py           # Add combat_phase to Session model
frontend/src/pages/GamePage.tsx    # Integrate CombatUI when in combat
frontend/src/types/index.ts        # Combat types
frontend/src/components/game/CombatStatus.tsx  # Enhance with action bar
```

---

## Technical Specification

### Data Models

#### New/Updated Python Models (`lambdas/dm/models.py`)

```python
from enum import Enum
from pydantic import BaseModel


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
    DEFEND = "defend"      # +2 AC this round
    FLEE = "flee"          # Dex check to escape
    USE_ITEM = "use_item"  # Potion, etc.


class CombatAction(BaseModel):
    """Player's chosen combat action."""
    action_type: CombatActionType
    target_id: str | None = None    # For attack actions
    item_id: str | None = None      # For use item actions


class CombatLogEntry(BaseModel):
    """Single entry in combat log."""
    round: int
    actor: str                      # "player" or enemy ID
    action: str                     # "attack", "defend", "flee"
    target: str | None = None
    roll: int | None = None         # Attack roll total
    damage: int | None = None
    result: str                     # "hit", "miss", "killed", "fled", "defended"
    narrative: str                  # AI-generated description


# Updated CombatState
class CombatState(BaseModel):
    """Active combat state - stored in session."""
    active: bool = False
    round: int = 1
    phase: CombatPhase = CombatPhase.COMBAT_START
    player_initiative: int = 0
    enemy_initiative: int = 0
    player_defending: bool = False  # +2 AC if true
    combat_log: list[CombatLogEntry] = []
```

#### TypeScript Types (`frontend/src/types/index.ts`)

```typescript
export type CombatPhase =
  | 'combat_start'
  | 'player_turn'
  | 'resolve_player'
  | 'enemy_turn'
  | 'combat_end';

export type CombatActionType = 'attack' | 'defend' | 'flee' | 'use_item';

export interface CombatAction {
  action_type: CombatActionType;
  target_id?: string;
  item_id?: string;
}

export interface CombatLogEntry {
  round: number;
  actor: string;
  action: string;
  target?: string;
  roll?: number;
  damage?: number;
  result: string;
  narrative: string;
}

export interface CombatResponse {
  active: boolean;
  round: number;
  phase: CombatPhase;
  your_hp: number;
  your_max_hp: number;
  enemies: Enemy[];
  available_actions: CombatActionType[];
  valid_targets: string[];
  combat_log: CombatLogEntry[];
}
```

### API Changes

#### Modified: POST /sessions/{id}/action

When in combat (`combat_state.active == true`), the request accepts an optional `combat_action` field:

**Request Body**:
```json
{
  "action": "attack goblin_a",
  "combat_action": {
    "action_type": "attack",
    "target_id": "goblin_a"
  }
}
```

Either `action` (free text) OR `combat_action` (structured) is accepted. If both provided, `combat_action` takes precedence.

**Response** (when in combat):
```json
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
        "roll": 15,
        "damage": 6,
        "result": "killed",
        "narrative": "Your sword finds its mark..."
      }
    ]
  },
  "character": {...},
  "dice_rolls": [...],
  "usage": {...}
}
```

---

## Implementation Steps

### Step 1: Update Combat Models

**Files**: `lambdas/dm/models.py`

Add `CombatPhase` enum, `CombatActionType` enum, `CombatAction` model, `CombatLogEntry` model. Update `CombatState` to include `phase`, `player_defending`, and `combat_log`.

**Validation**:
- [ ] Models import correctly
- [ ] Pydantic validation works

### Step 2: Create Combat Action Parser

**Files**: `lambdas/dm/combat_parser.py` (NEW)

Create parser to convert free text to structured `CombatAction`:

```python
def parse_combat_action(
    text: str,
    valid_targets: list[str]
) -> CombatAction | None:
    """Parse free text into combat action.

    Examples:
        "attack goblin" -> CombatAction(type=ATTACK, target_id="goblin_a")
        "run away" -> CombatAction(type=FLEE)
        "defend" -> CombatAction(type=DEFEND)
        "drink potion" -> CombatAction(type=USE_ITEM, item_id="health_potion")
    """
```

Use simple keyword matching (no AI needed):
- Contains "attack/hit/strike/kill" + target name -> ATTACK
- Contains "defend/block/guard" -> DEFEND
- Contains "flee/run/escape" -> FLEE
- Contains "drink/use/potion" -> USE_ITEM

**Validation**:
- [ ] Unit tests for all action types
- [ ] Fuzzy target matching works

### Step 3: Create Combat Narrator

**Files**: `lambdas/dm/combat_narrator.py` (NEW)

Create focused narrator that only describes predetermined outcomes:

```python
COMBAT_NARRATOR_PROMPT = """You are narrating combat in a dark fantasy RPG.
Describe ONLY the outcome provided. Do not add extra attacks or change results.

Mechanical Result:
- Attacker: {attacker}
- Target: {target}
- Action: {action}
- Roll: {roll} vs AC {ac} = {hit_or_miss}
- Damage: {damage} (target now at {target_hp}/{target_max_hp} HP)
- Result: {result}

Write 1-2 vivid sentences describing this moment.
Do NOT include dice numbers. Do NOT add moralizing.
Style: brutal, visceral, dark fantasy."""


async def narrate_attack(
    attack_result: AttackResult,
    ai_client: BedrockClient
) -> str:
    """Generate narrative for single attack outcome."""


async def narrate_round(
    round_results: list[AttackResult],
    ai_client: BedrockClient
) -> str:
    """Generate combined narrative for full round."""
```

Keep prompts minimal (~200 tokens input, ~50 tokens output per attack) to control costs.

**Validation**:
- [ ] Narrator doesn't hallucinate outcomes
- [ ] Token usage stays under 300 per round

### Step 4: Refactor Combat Resolver for Turn-by-Turn

**Files**: `lambdas/dm/combat.py`

Refactor existing `CombatResolver` to handle single-turn resolution:

```python
def resolve_player_turn(
    character: Character,
    action: CombatAction,
    enemies: list[CombatEnemy],
    player_defending: bool
) -> tuple[AttackResult | None, bool]:
    """Resolve player's single turn.

    Returns:
        (attack_result, fled_successfully)
    """

    if action.action_type == CombatActionType.DEFEND:
        # No attack result, but player gets +2 AC for enemy phase
        return None, False

    if action.action_type == CombatActionType.FLEE:
        # Dex check: roll d20 + DEX mod vs DC 10
        return None, roll_flee_check(character)

    if action.action_type == CombatActionType.ATTACK:
        target = find_enemy(action.target_id, enemies)
        return resolve_player_attack(character, target), False


def resolve_enemy_phase(
    character: Character,
    enemies: list[CombatEnemy],
    player_defending: bool
) -> list[AttackResult]:
    """All living enemies attack player."""
    player_ac = calculate_player_ac(character, player_defending)
    results = []
    for enemy in enemies:
        if not enemy.is_dead:
            results.append(resolve_enemy_attack(enemy, character, player_ac))
    return results
```

**Validation**:
- [ ] Defend grants +2 AC
- [ ] Flee check uses DEX modifier
- [ ] All living enemies attack

### Step 5: Update DM Service for Combat Phases

**Files**: `lambdas/dm/service.py`

Refactor `_process_combat_action()` to use combat phase state machine:

```python
async def _process_combat_action(
    self,
    session: Session,
    character: Character,
    action: str,
    combat_action: CombatAction | None
) -> ActionResponse:
    """Process combat using phase state machine."""

    combat_state = session.combat_state

    # Parse action if not structured
    if not combat_action:
        combat_action = parse_combat_action(action, get_valid_targets(session))
        if not combat_action:
            # Default to attack first living enemy
            combat_action = CombatAction(
                action_type=CombatActionType.ATTACK,
                target_id=session.combat_enemies[0].id
            )

    # PLAYER TURN: Resolve player action
    attack_result, fled = resolve_player_turn(
        character, combat_action, session.combat_enemies,
        combat_state.player_defending
    )

    if fled:
        # Combat ends, player escaped
        return self._end_combat(session, character, victory=False, fled=True)

    # Check if all enemies dead after player turn
    if all(e.is_dead for e in session.combat_enemies):
        return self._end_combat(session, character, victory=True)

    # ENEMY TURN: All enemies attack
    player_defending = combat_action.action_type == CombatActionType.DEFEND
    enemy_results = resolve_enemy_phase(
        character, session.combat_enemies, player_defending
    )

    # Check if player dead
    if character.hp <= 0:
        return self._end_combat(session, character, victory=False, died=True)

    # Generate narrative for full round
    all_results = ([attack_result] if attack_result else []) + enemy_results
    narrative = await narrate_round(all_results, self.ai_client)

    # Update combat state
    combat_state.round += 1
    combat_state.phase = CombatPhase.PLAYER_TURN
    combat_state.player_defending = False

    # Build and return response
    return self._build_combat_response(session, character, narrative, all_results)
```

**Validation**:
- [ ] Phase transitions correctly
- [ ] Combat ends on victory/death/flee
- [ ] XP awarded on victory

### Step 6: Update Handler for Combat Actions

**Files**: `lambdas/dm/handler.py`

Update request model and action handler to accept structured combat actions:

```python
class ActionRequest(BaseModel):
    """Player action request."""
    action: str
    combat_action: CombatAction | None = None


@app.post("/sessions/<session_id>/action")
def process_action(session_id: str):
    # ... existing setup ...
    request = ActionRequest(**app.current_event.json_body)

    response = dm_service.process_action(
        session_id=session_id,
        user_id=user_id,
        action=request.action,
        combat_action=request.combat_action  # NEW
    )
    return response.model_dump()
```

**Validation**:
- [ ] Both free text and structured actions work
- [ ] Structured action takes precedence

### Step 7: Create Frontend Combat UI Components

**Files**:
- `frontend/src/components/game/CombatUI.tsx` (NEW)
- `frontend/src/components/game/ActionBar.tsx` (NEW)
- `frontend/src/components/game/CombatLog.tsx` (NEW)
- `frontend/src/components/game/EnemyCard.tsx` (NEW)

Create main combat UI:

```typescript
// CombatUI.tsx
interface CombatUIProps {
  combat: CombatResponse;
  onAction: (action: CombatAction) => void;
  isLoading: boolean;
}

export function CombatUI({ combat, onAction, isLoading }: CombatUIProps) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);

  return (
    <div className="combat-ui bg-gray-900 border border-red-800 rounded-lg p-4">
      {/* Round indicator */}
      <div className="text-center text-red-500 font-bold mb-4">
        ⚔️ COMBAT - Round {combat.round}
      </div>

      {/* Enemy list */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        {combat.enemies.map(enemy => (
          <EnemyCard
            key={enemy.id}
            enemy={enemy}
            isSelected={selectedTarget === enemy.id}
            onSelect={() => setSelectedTarget(enemy.id)}
            selectable={combat.valid_targets.includes(enemy.id)}
          />
        ))}
      </div>

      {/* Player status */}
      <div className="text-center mb-4">
        <span className="text-white">Your HP: </span>
        <span className={combat.your_hp < combat.your_max_hp / 3 ? 'text-red-500' : 'text-green-500'}>
          {combat.your_hp}/{combat.your_max_hp}
        </span>
      </div>

      {/* Action bar */}
      <ActionBar
        availableActions={combat.available_actions}
        selectedTarget={selectedTarget}
        hasValidTarget={combat.valid_targets.length > 0}
        onAction={onAction}
        disabled={isLoading}
      />

      {/* Combat log */}
      <CombatLog entries={combat.combat_log} />
    </div>
  );
}
```

**Validation**:
- [ ] All action buttons render
- [ ] Target selection works
- [ ] Loading state disables actions

### Step 8: Create ActionBar Component

**Files**: `frontend/src/components/game/ActionBar.tsx`

```typescript
interface ActionBarProps {
  availableActions: CombatActionType[];
  selectedTarget: string | null;
  hasValidTarget: boolean;
  onAction: (action: CombatAction) => void;
  disabled: boolean;
}

export function ActionBar({
  availableActions,
  selectedTarget,
  hasValidTarget,
  onAction,
  disabled
}: ActionBarProps) {
  return (
    <div className="flex flex-wrap gap-2 justify-center">
      {availableActions.includes('attack') && (
        <button
          onClick={() => onAction({ action_type: 'attack', target_id: selectedTarget! })}
          disabled={disabled || !selectedTarget}
          className="px-4 py-2 bg-red-700 hover:bg-red-600 disabled:bg-gray-700
                     text-white rounded font-bold transition-colors"
        >
          ⚔️ Attack
        </button>
      )}

      {availableActions.includes('defend') && (
        <button
          onClick={() => onAction({ action_type: 'defend' })}
          disabled={disabled}
          className="px-4 py-2 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700
                     text-white rounded font-bold transition-colors"
        >
          🛡️ Defend
        </button>
      )}

      {availableActions.includes('flee') && (
        <button
          onClick={() => onAction({ action_type: 'flee' })}
          disabled={disabled}
          className="px-4 py-2 bg-yellow-700 hover:bg-yellow-600 disabled:bg-gray-700
                     text-white rounded font-bold transition-colors"
        >
          🏃 Flee
        </button>
      )}

      {availableActions.includes('use_item') && (
        <button
          onClick={() => onAction({ action_type: 'use_item' })}
          disabled={disabled}
          className="px-4 py-2 bg-green-700 hover:bg-green-600 disabled:bg-gray-700
                     text-white rounded font-bold transition-colors"
        >
          🧪 Item
        </button>
      )}
    </div>
  );
}
```

**Validation**:
- [ ] Attack requires target selection
- [ ] All buttons have hover/disabled states

### Step 9: Create CombatLog Component

**Files**: `frontend/src/components/game/CombatLog.tsx`

```typescript
interface CombatLogProps {
  entries: CombatLogEntry[];
}

export function CombatLog({ entries }: CombatLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [entries]);

  if (entries.length === 0) return null;

  return (
    <div
      ref={scrollRef}
      className="mt-4 max-h-32 overflow-y-auto bg-gray-800 rounded p-2 text-sm"
    >
      <div className="text-gray-500 text-xs mb-1">Combat Log</div>
      {entries.map((entry, i) => (
        <div key={i} className={`mb-1 ${entry.actor === 'player' ? 'text-blue-300' : 'text-red-300'}`}>
          <span className="text-gray-500">R{entry.round}</span>{' '}
          <span className="font-bold">{entry.actor === 'player' ? 'You' : entry.actor}</span>{' '}
          {entry.result === 'hit' && `hit ${entry.target} for ${entry.damage} damage`}
          {entry.result === 'miss' && `missed ${entry.target}`}
          {entry.result === 'killed' && `killed ${entry.target}!`}
          {entry.result === 'defended' && 'raised their guard'}
          {entry.result === 'fled' && 'fled from combat'}
        </div>
      ))}
    </div>
  );
}
```

**Validation**:
- [ ] Auto-scrolls to latest entry
- [ ] Color coding works

### Step 10: Update GamePage Integration

**Files**: `frontend/src/pages/GamePage.tsx`

Integrate `CombatUI` when combat is active:

```typescript
// In GamePage component
const handleCombatAction = useCallback(async (combatAction: CombatAction) => {
  if (!sessionId) return;

  setLoading(true);
  try {
    const response = await api.sendAction(sessionId, '', combatAction);
    // Update state from response...
  } finally {
    setLoading(false);
  }
}, [sessionId]);

// In render
{combatActive && combat && (
  <CombatUI
    combat={combat}
    onAction={handleCombatAction}
    isLoading={loading}
  />
)}

{/* Hide regular action input during combat - use ActionBar instead */}
{!combatActive && (
  <ActionInput
    onAction={handleAction}
    disabled={loading || sessionEnded}
  />
)}
```

**Validation**:
- [ ] CombatUI shows when combatActive=true
- [ ] ActionInput hides during combat
- [ ] Combat actions update state

### Step 11: Update API Service

**Files**: `frontend/src/services/api.ts`

Add combat action support:

```typescript
async sendAction(
  sessionId: string,
  action: string,
  combatAction?: CombatAction
): Promise<ActionResponse> {
  const response = await this.fetch(`/sessions/${sessionId}/action`, {
    method: 'POST',
    body: JSON.stringify({ action, combat_action: combatAction }),
  });
  return response.json();
}
```

**Validation**:
- [ ] Combat action sent in request body
- [ ] Response parsed correctly

### Step 12: Unit Tests for Combat System

**Files**:
- `lambdas/tests/test_combat_parser.py` (NEW)
- `lambdas/tests/test_combat_narrator.py` (NEW)
- `lambdas/tests/test_combat_phases.py` (NEW)

Test cases:
- Parser: attack/defend/flee/use_item from free text
- Narrator: doesn't hallucinate, stays under token limit
- Phases: correct state transitions, defend grants AC bonus, flee uses DEX

**Validation**:
- [ ] All tests pass
- [ ] Coverage >= 80% for new files

---

## Testing Requirements

### Unit Tests

1. **Combat Parser**: Parse "attack goblin", "run away", "defend", "drink potion"
2. **Combat Resolver**: Defend grants +2 AC, flee check uses DEX, damage calculation
3. **Combat State Machine**: Phase transitions, victory/death/flee end conditions
4. **Narrator**: Output matches expected format, token count acceptable

### Integration Tests

1. Full combat flow: initiate -> player attack -> enemy attack -> player wins
2. Combat persists across API calls (refresh page, continue combat)
3. XP awarded correctly on victory
4. Death triggers correctly when HP <= 0
5. Flee escapes combat

### Manual Testing

1. Start combat with 3 goblins
2. Attack and kill one goblin
3. Defend for a round (verify lower damage taken)
4. Flee successfully
5. Die in combat, verify death screen

---

## Integration Test Plan

### Prerequisites

- Backend deployed: `cd cdk && cdk deploy --all -c environment=prod -c certificateArn=...`
- Site accessible at https://chaos.jurigregg.com
- Character created at level 1

### Test Steps

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Create new character and start adventure | Session starts in exploration mode | ☐ |
| 2 | Type "I look for trouble" or similar | DM may initiate combat | ☐ |
| 3 | When combat starts, verify UI changes | CombatUI shows with enemy list, action buttons | ☐ |
| 4 | Click an enemy to select target | Enemy card highlights | ☐ |
| 5 | Click Attack button | Attack resolves, narrative appears, enemy HP updates | ☐ |
| 6 | Wait for enemy turn | Enemies attack, player HP may decrease | ☐ |
| 7 | Click Defend button | Next enemy attacks should do less damage | ☐ |
| 8 | Refresh page mid-combat | Combat state restored, same round/enemies | ☐ |
| 9 | Kill all enemies | Victory message, XP gained, return to exploration | ☐ |
| 10 | In new combat, click Flee | Dex check, if successful exits combat | ☐ |

### Error Scenarios

| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Attack without target | Don't select enemy, click Attack | Button disabled or error message | ☐ |
| Network error mid-combat | Disconnect then retry | Error message, can retry action | ☐ |
| Character death | Let enemies kill you | Death screen shows | ☐ |

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| InvalidTargetError | Target enemy not in valid_targets | Return 400 with message |
| NotInCombatError | Combat action when not in combat | Return 400, explain |
| NoItemError | Use item when inventory empty | Return 400, explain |

### Edge Cases

- Player types free text during combat: Parse and convert to action
- All enemies die on same round: Victory triggers immediately
- Player at 1 HP, enemy hits: Death triggers, session ends
- Flee fails: Player stays in combat, enemies get attacks

---

## Cost Impact

### AI Calls

**Current (before)**:
- Single large call per combat (~800 tokens)

**New (after)**:
- Combat narrator per round: ~200 tokens input, ~50 tokens output
- Average combat: 4-6 rounds = 800-1200 tokens input, 200-300 output
- ~$0.001-0.002 per combat (negligible increase)

### AWS

- No new resources
- Slightly more DynamoDB writes (combat state per round)
- Estimate: <$0.10/month additional

---

## Open Questions

1. **Item usage**: Should USE_ITEM show inventory modal, or auto-use best potion?
   - Recommendation: Auto-use health potion for MVP, modal later

2. **Multiple player attacks**: Higher-level fighters get multiple attacks?
   - Recommendation: Out of scope for MVP, single attack per round

3. **Targeting priority**: When player types "attack" without target, which enemy?
   - Recommendation: First living enemy in list

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Init spec is comprehensive, state machine well-defined |
| Feasibility | 9 | Foundation exists (combat.py, bestiary, dice), mostly UI work |
| Completeness | 8 | Covers core combat, items/spells out of scope |
| Alignment | 9 | Fits architecture, minimal cost increase |
| **Overall** | 8.75 | Ready to implement |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
