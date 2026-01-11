# PRP-14: Combat Polish

**Created**: 2026-01-11
**Initial**: `initials/init-14-combat-polish.md`
**Status**: Ready

---

## Overview

### Problem Statement
The turn-based combat system (from init-12) is functional but has several rough edges discovered during testing:
1. **Narrator prompt artifacts** leak into player-visible text (e.g., `[DM]:`, `Narrative:`, `State Changes:`)
2. **Narrator hallucination** - AI invents characters/actions not in the actual combat results
3. **Narrative truncation** - responses cut off mid-sentence due to low `max_tokens` (currently 200)
4. **DM solo combat** - when combat starts via free text, DM sometimes narrates multiple rounds without player input
5. **Enemy name disambiguation** - multiple enemies of the same type show as "Fighter", "Fighter" instead of "Fighter 1", "Fighter 2"
6. **Free text target parsing** - unclear behavior when player types "Attack Fighter" with 3 fighters

### Proposed Solution
1. Add missing cleaning patterns to `combat_narrator.py`
2. Strengthen narrator system prompt to prevent hallucination
3. Increase narrator `max_tokens` from 200 to 300
4. Reinforce in `output_format.py` that combat initiation is handoff-only (no resolution)
5. Add numbered suffixes to enemy names at spawn time in `bestiary.py`
6. Update `combat_parser.py` to default to first living enemy when type is ambiguous

### Success Criteria
- [ ] No prompt artifacts (`[DM]:`, `Narrative:`, `State Changes:`) in player-visible text
- [ ] Narrator only describes provided combat outcomes (no invented characters/actions)
- [ ] Narratives complete (no mid-sentence truncation)
- [ ] Combat initiation hands off to turn-based UI immediately (no DM solo combat)
- [ ] Multiple same-type enemies have numbered names (e.g., "Goblin 1", "Goblin 2")
- [ ] Free text targeting predictably selects first living enemy of matching type

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview
- `docs/DECISIONS.md` - ADR-012 (Pydantic validators)
- `initials/init-12-turn-based-combat.md` - Original combat implementation

### Dependencies
- Required: init-12-turn-based-combat (COMPLETE)
- Optional: None

### Files to Modify/Create
```
lambdas/dm/combat_narrator.py     # Add cleaning patterns, strengthen system prompt
lambdas/dm/bedrock_client.py      # Increase narrator max_tokens
lambdas/dm/bestiary.py            # Add numbered suffixes at spawn
lambdas/dm/combat_parser.py       # Clarify target selection logic
lambdas/dm/prompts/output_format.py # Reinforce combat handoff rules
frontend/src/components/game/EnemyCard.tsx # (optional) Display numbered names
```

---

## Technical Specification

### Data Models
No model changes required. Enemy names will include the number suffix in the existing `name` field.

### API Changes
No API changes. Response format remains the same.

### Component Structure
No new components. Modifications to existing files only.

---

## Implementation Steps

### Step 1: Add Missing Cleaning Patterns
**Files**: `lambdas/dm/combat_narrator.py`

Add patterns to `PROMPT_LEAK_PATTERNS` and `INLINE_MARKERS` to catch additional artifacts:

```python
# Add to PROMPT_LEAK_PATTERNS (lines 16-39)
r"^\[DM\]:?\s*$",           # [DM] or [DM]: header
r"^\[Dungeon Master\]:?\s*$",
r"^DM:\s*$",
r"^Dungeon Master:\s*$",

# Add to INLINE_MARKERS (lines 51-56)
r"\[DM\]:?\s*",             # [DM]: inline prefix
r"\[Dungeon Master\]:?\s*",
r"DM:\s*",                  # No ^ anchor - match anywhere
r"Dungeon Master:\s*",
```

**Validation**:
- [ ] Unit tests pass
- [ ] Lint passes

### Step 2: Strengthen Narrator System Prompt
**Files**: `lambdas/dm/combat_narrator.py`

Update `COMBAT_NARRATOR_SYSTEM_PROMPT` (lines 119-128) to prevent hallucination:

```python
COMBAT_NARRATOR_SYSTEM_PROMPT = """You are a combat narrator for a dark fantasy RPG. Describe combat outcomes vividly.

CRITICAL RULES:
1. Output ONLY narrative prose. No headers, no markers, no meta-commentary.
2. Describe EXACTLY what is given. The combatants are:
   - The player character (named in the prompt)
   - The enemies listed in the prompt
   NO OTHER CHARACTERS EXIST. Do not invent party members, allies, or bystanders.
3. NEVER mention HP, damage numbers, or game mechanics. NO NUMBERS.
4. 1-2 vivid sentences per action. Brutal, visceral style.
5. Describe deaths dramatically when indicated.
6. Complete your sentences. Never stop mid-word.
7. Output the narrative directly with no preamble or conclusion."""
```

**Validation**:
- [ ] Unit tests pass
- [ ] Lint passes

### Step 3: Increase Narrator max_tokens
**Files**: `lambdas/dm/bedrock_client.py`

Update `narrate_combat` method (line 173) to use higher token limit:

```python
# Change from:
max_tokens=200,  # Short narrative only

# To:
max_tokens=300,  # Allow complete sentences
```

**Validation**:
- [ ] Unit tests pass
- [ ] Lint passes

### Step 4: Reinforce Combat Handoff in Output Format
**Files**: `lambdas/dm/prompts/output_format.py`

Add stronger language to the combat rules section (lines 53-97):

```python
## COMBAT RULES - CRITICAL

Combat uses a TURN-BASED SYSTEM handled by the server. Your role is LIMITED:

### Starting Combat
When a hostile encounter begins:
1. Write a SHORT narrative (1-2 sentences) describing the enemies appearing
2. Include the "enemies" array with enemy stats
3. DO NOT roll any dice
4. DO NOT resolve any attacks
5. DO NOT narrate combat outcomes
6. DO NOT simulate combat rounds - the FIRST turn happens via UI

AFTER you output the enemies array, STOP. The server takes over.
The player will see UI buttons (Attack, Defend, Flee) and make their choice.
You will NOT receive any more messages until combat ends.

WRONG - Never do this:
"The goblin attacks you, rolling a 15... you dodge and counter-attack..."
(This is wrong because you're simulating combat rounds)

RIGHT - Do this:
"A goblin snarls and raises its blade!"
{"enemies": [{"name": "Goblin", "hp": 4, "ac": 12}]}
(Then STOP - let the server handle combat)
```

**Validation**:
- [ ] Unit tests pass
- [ ] Lint passes

### Step 5: Add Numbered Enemy Names at Spawn
**Files**: `lambdas/dm/bestiary.py`

Modify `spawn_enemy` to accept an optional index parameter, and create a new `spawn_enemies` function that handles numbering:

```python
def spawn_enemy(enemy_type: str, index: int | None = None) -> CombatEnemy:
    """Spawn a single enemy from the bestiary.

    Args:
        enemy_type: Enemy type name (e.g., "goblin", "orc")
        index: Optional 1-based index for disambiguation (e.g., 1, 2, 3)

    Returns:
        CombatEnemy with rolled HP and stats
    """
    # ... existing lookup logic ...

    name = template["name"]
    if index is not None:
        name = f"{name} {index}"

    return CombatEnemy(
        id=str(uuid4()),
        name=name,
        # ... rest of fields ...
    )


def spawn_enemies(enemy_types: list[str]) -> list[CombatEnemy]:
    """Spawn multiple enemies with numbered names for duplicates.

    Args:
        enemy_types: List of enemy type names

    Returns:
        List of CombatEnemy with numbered names for duplicates
    """
    # Count occurrences of each type
    type_counts: dict[str, int] = {}
    for t in enemy_types:
        normalized = t.lower().strip()
        type_counts[normalized] = type_counts.get(normalized, 0) + 1

    # Track which index we're on for each type
    type_indices: dict[str, int] = {}
    enemies = []

    for enemy_type in enemy_types:
        normalized = enemy_type.lower().strip()
        count = type_counts[normalized]

        if count > 1:
            # Multiple of this type - add index
            idx = type_indices.get(normalized, 0) + 1
            type_indices[normalized] = idx
            enemies.append(spawn_enemy(enemy_type, index=idx))
        else:
            # Only one of this type - no index needed
            enemies.append(spawn_enemy(enemy_type))

    return enemies
```

**Also update** `lambdas/dm/service.py` `_initiate_combat` method (lines 965-1030) to use `spawn_enemies`:

```python
def _initiate_combat(self, session: dict, enemies: list[Enemy]) -> None:
    """Start combat with enemies from Claude's response."""
    from dm.bestiary import spawn_enemies

    enemy_types = [e.name for e in enemies]

    try:
        combat_enemies = spawn_enemies(enemy_types)
    except ValueError as e:
        # Handle unknown enemy types with fallback
        # ... existing fallback logic ...
```

**Validation**:
- [ ] Unit tests for spawn_enemies with duplicates
- [ ] Unit tests for spawn_enemies with mixed types
- [ ] Lint passes

### Step 6: Clarify Target Selection in Combat Parser
**Files**: `lambdas/dm/combat_parser.py`

Update `_find_target` function (lines 144-184) to explicitly document behavior and ensure deterministic selection:

```python
def _find_target(text: str, enemies: list[CombatEnemy]) -> CombatEnemy | None:
    """Find target enemy from player's text input.

    Matching priority:
    1. Full name match (case-insensitive): "Goblin 1" matches "Goblin 1"
    2. First word match: "goblin" matches "Goblin 1" (first living match)
    3. Numbered suffix: "1" or "2" matches enemy with that number

    If multiple enemies match (e.g., "attack goblin" with Goblin 1 and Goblin 2),
    returns the FIRST living enemy in list order.

    Args:
        text: Player's input text
        enemies: List of enemies in combat

    Returns:
        First matching living enemy, or None
    """
    text_lower = text.lower().strip()
    living_enemies = [e for e in enemies if e.hp > 0]

    if not living_enemies:
        return None

    # 1. Full name match
    for enemy in living_enemies:
        if enemy.name.lower() == text_lower or enemy.name.lower() in text_lower:
            return enemy

    # 2. First word match (e.g., "goblin" matches "Goblin 1")
    for enemy in living_enemies:
        first_word = enemy.name.split()[0].lower()
        if first_word in text_lower:
            return enemy  # Return FIRST match

    # 3. Numbered suffix match (e.g., "attack 2" targets enemy with "2" suffix)
    # Use exact suffix match to avoid "1" matching "Goblin 11"
    match = re.search(r"\b(\d+)\b", text)
    if match:
        num = match.group(1)
        for enemy in living_enemies:
            if enemy.name.endswith(f" {num}"):
                return enemy

    return None
```

**Validation**:
- [ ] Unit tests for "attack goblin" with multiple goblins (first returned)
- [ ] Unit tests for "attack goblin 2" (specific goblin returned)
- [ ] Lint passes

---

## Testing Requirements

### Unit Tests

**File**: `lambdas/dm/test_combat_narrator.py` (new tests to add)
```python
def test_clean_narrator_output_strips_dm_prefix():
    """Test that [DM]: prefix is stripped."""
    text = "[DM]: The goblin strikes!"
    result = clean_narrator_output(text)
    assert result == "The goblin strikes!"

def test_clean_narrator_output_strips_dungeon_master():
    """Test that Dungeon Master: prefix is stripped."""
    text = "Dungeon Master: The blade finds its mark."
    result = clean_narrator_output(text)
    assert result == "The blade finds its mark."

def test_clean_narrator_output_strips_state_changes_header():
    """Test that State Changes: line is removed."""
    text = "You strike the goblin.\nState Changes:\nThe battle continues."
    result = clean_narrator_output(text)
    assert "State Changes" not in result
```

**File**: `lambdas/dm/test_bestiary.py` (new tests to add)
```python
def test_spawn_enemies_numbers_duplicates():
    """Test that duplicate enemy types get numbered names."""
    enemies = spawn_enemies(["goblin", "goblin", "goblin"])
    names = [e.name for e in enemies]
    assert names == ["Goblin 1", "Goblin 2", "Goblin 3"]

def test_spawn_enemies_no_number_for_singles():
    """Test that single enemy types don't get numbered."""
    enemies = spawn_enemies(["goblin", "orc", "skeleton"])
    names = [e.name for e in enemies]
    assert names == ["Goblin", "Orc", "Skeleton"]

def test_spawn_enemies_mixed_numbering():
    """Test mixed duplicates and singles."""
    enemies = spawn_enemies(["goblin", "orc", "goblin"])
    names = [e.name for e in enemies]
    assert names == ["Goblin 1", "Orc", "Goblin 2"]
```

**File**: `lambdas/dm/test_combat_parser.py` (new tests to add)
```python
def test_find_target_first_match_for_ambiguous():
    """Test that ambiguous type matches first living enemy."""
    enemies = [
        CombatEnemy(id="1", name="Goblin 1", hp=4, max_hp=4, ac=12),
        CombatEnemy(id="2", name="Goblin 2", hp=4, max_hp=4, ac=12),
    ]
    result = _find_target("attack goblin", enemies)
    assert result.name == "Goblin 1"

def test_find_target_specific_number():
    """Test that numbered suffix targets specific enemy."""
    enemies = [
        CombatEnemy(id="1", name="Goblin 1", hp=4, max_hp=4, ac=12),
        CombatEnemy(id="2", name="Goblin 2", hp=4, max_hp=4, ac=12),
    ]
    result = _find_target("attack goblin 2", enemies)
    assert result.name == "Goblin 2"

def test_find_target_number_exact_suffix():
    """Test that '1' doesn't match 'Goblin 11' (edge case)."""
    enemies = [
        CombatEnemy(id="1", name="Goblin 1", hp=4, max_hp=4, ac=12),
        CombatEnemy(id="11", name="Goblin 11", hp=4, max_hp=4, ac=12),
    ]
    result = _find_target("attack 1", enemies)
    assert result.name == "Goblin 1"  # Not Goblin 11
```

### Integration Tests
- Test combat narrator with various edge cases (via manual API calls)
- Test enemy spawning through full combat flow

### Manual Testing
1. Start new session
2. Trigger combat with multiple goblins
3. Verify enemy pills show "Goblin 1", "Goblin 2", etc.
4. Attack using free text "attack goblin" - verify first goblin targeted
5. Attack using "attack goblin 2" - verify second goblin targeted
6. Observe narrative for artifacts and hallucinations

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites
- Backend deployed: `cd lambdas && zip -r /tmp/dm-update.zip dm/ shared/ && aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip`
- Frontend running: `cd frontend && npm run dev` or deployed
- Browser DevTools open (Console + Network tabs)

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Create character, start session | Session loads | ☐ |
| 2 | Type "I attack the goblin standing near the door" | Combat initiates with enemy list, no DM narrated combat rounds | ☐ |
| 3 | Observe enemy pills in combat UI | Enemies have names, single types show "Goblin", multiple show "Goblin 1", "Goblin 2" | ☐ |
| 4 | Click Attack button (or type "attack") | Narrative describes only player and enemies, no invented characters | ☐ |
| 5 | Complete combat until death or victory | Narratives are complete sentences, no mid-word cutoff | ☐ |
| 6 | Check all DM responses for artifacts | No "[DM]:", "Narrative:", "State Changes:" visible | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Truncated narrative | N/A (should not occur with fix) | Narrative ends with complete sentence | ☐ |
| Hallucinated character | N/A (should not occur with fix) | Only player and listed enemies mentioned | ☐ |

### Browser Checks
- [ ] No CORS errors in Console
- [ ] No JavaScript errors in Console
- [ ] API requests visible in Network tab
- [ ] Responses are 2xx (not 4xx/5xx)
- [ ] Enemy names display correctly in combat UI

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Unknown enemy type | AI specifies enemy not in bestiary | Falls back to AI-provided stats (existing behavior) |

### Edge Cases
- Single enemy of a type: No numbering applied (remains "Goblin" not "Goblin 1")
- All enemies dead before parsing: `_find_target` returns None, default action used
- Empty enemy list: No combat UI displayed

---

## Cost Impact

### Claude API (Mistral via Bedrock)
- Narrator max_tokens increased from 200 to 300
- Estimated additional output per combat round: ~50 tokens
- At 100 combat rounds/day: 5000 extra tokens
- Cost: 5000 × $3/1M = $0.015/day = ~$0.45/month

### AWS
- No new resources
- No infrastructure changes

---

## Open Questions

1. **Should we show enemy AC in the UI?** Currently hidden but in the data.
   - Decision: Out of scope for this PRP. Can be added later.

2. **Should numbered names be shown in narrative too?** (e.g., "Goblin 1 strikes!")
   - Decision: Yes, the name includes the number, so narratives will naturally use it.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements from testing are specific and actionable |
| Feasibility | 10 | All changes are isolated modifications to existing code |
| Completeness | 9 | All issues identified have solutions; testing plan is thorough |
| Alignment | 10 | Minor cost increase, improves UX, follows existing patterns |
| **Overall** | 9.5 | High confidence - polish work with clear scope |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
