# PRP-05: DM System Prompt

**Created**: 2026-01-01
**Initial**: `initials/init-05-dm-system-prompt.md`
**Status**: Ready

---

## Overview

### Problem Statement
The game needs an AI Dungeon Master that can narrate adventures, apply BECMI D&D rules, track combat, and output structured state changes. The system prompt must be optimized for Anthropic's prompt caching to minimize API costs (per ADR-006), while enabling mature dark fantasy content (per ADR-007).

### Proposed Solution
Create a modular prompt builder system in `lambdas/dm/prompts/` that:
1. Constructs a ~2000 token cacheable system prompt with DM identity, BECMI rules, and output format
2. Builds dynamic context from character state, session data, and message history
3. Parses Claude's response to extract narrative and structured state changes (JSON)
4. Provides Pydantic models for response validation

### Success Criteria
- [ ] System prompt builds correctly with all sections (~2000 tokens)
- [ ] Campaign-specific content loads for each of 4 settings
- [ ] Character state formats compactly (~150 tokens)
- [ ] Message history truncates to fit token budget (~800 tokens max)
- [ ] Output JSON parses reliably from Claude responses
- [ ] State changes (hp_delta, gold_delta, xp_delta, inventory, location) extracted
- [ ] Dice rolls captured with type, roll, modifier, total, success
- [ ] Combat state (enemies list, combat_active flag) tracked
- [ ] Unit tests for all prompt builders (>80% coverage)
- [ ] Integration test with mock Claude response

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview, token budgets
- `docs/DECISIONS.md` - ADR-001 (Haiku 3), ADR-003 (BECMI), ADR-006 (prompt caching), ADR-007 (mature content)
- `initials/init-05-dm-system-prompt.md` - Full specification with prompt text

### Dependencies
- **Required**: init-03-session-api (Session model with message_history, campaign_setting)
- **Required**: init-02-character-api (Character model with stats)
- **Optional**: init-06-action-handler (will consume these prompts)

### Files to Modify/Create
```
lambdas/dm/__init__.py              # Package init
lambdas/dm/prompts/__init__.py      # Prompts subpackage
lambdas/dm/prompts/system_prompt.py # Main cacheable system prompt
lambdas/dm/prompts/rules.py         # BECMI rules reference text
lambdas/dm/prompts/campaigns.py     # Campaign-specific openings
lambdas/dm/prompts/output_format.py # JSON output format instructions
lambdas/dm/prompts/context.py       # Dynamic context builder
lambdas/dm/models.py                # Response parsing models
lambdas/dm/parser.py                # JSON extraction from response
lambdas/tests/test_dm_prompts.py    # Unit tests for prompt builders
lambdas/tests/test_dm_parser.py     # Unit tests for response parser
```

---

## Technical Specification

### Data Models

```python
# lambdas/dm/models.py

class StateChanges(BaseModel):
    """State changes to apply to game state after DM response."""
    hp_delta: int = 0
    gold_delta: int = 0
    xp_delta: int = 0
    location: str | None = None
    inventory_add: list[str] = Field(default_factory=list)
    inventory_remove: list[str] = Field(default_factory=list)
    world_state: dict[str, Any] = Field(default_factory=dict)

class DiceRoll(BaseModel):
    """Record of a dice roll made by the DM."""
    type: str  # attack, damage, save, skill, initiative
    roll: int
    modifier: int = 0
    total: int
    success: bool | None = None

class Enemy(BaseModel):
    """Enemy state during combat."""
    name: str
    hp: int
    ac: int
    max_hp: int | None = None

class DMResponse(BaseModel):
    """Parsed DM response with narrative and state changes."""
    narrative: str
    state_changes: StateChanges = Field(default_factory=StateChanges)
    dice_rolls: list[DiceRoll] = Field(default_factory=list)
    combat_active: bool = False
    enemies: list[Enemy] = Field(default_factory=list)
```

### Prompt Builder Interface

```python
# lambdas/dm/prompts/context.py

class DMPromptBuilder:
    """Builds prompts for the DM Lambda."""

    def build_system_prompt(self, campaign: str = "default") -> str:
        """Build the cacheable system prompt (~2000 tokens).

        Combines:
        - DM identity and personality
        - BECMI rules reference
        - Output format instructions
        - Campaign-specific setting
        - Content guidelines
        """
        pass

    def build_context(
        self,
        character: Character,
        session: Session,
    ) -> str:
        """Build the dynamic context section (~500-800 tokens).

        Includes:
        - Character stats block
        - Current location and world state
        - Recent message history (last 10-15)
        """
        pass

    def build_user_message(self, action: str) -> str:
        """Format the player's action for the API call."""
        return f"[Player Action]: {action}"
```

### Token Budget

| Section | Target Tokens | Cache Status |
|---------|---------------|--------------|
| System prompt | ~2000 | Cached (90% savings) |
| Character state | ~150 | Dynamic |
| World state | ~100 | Dynamic |
| Message history | ~800 | Dynamic (last 10-15 msgs) |
| Player action | ~50 | Dynamic |
| **Total input** | **~3100** | |
| DM response | ~500 | Output |

---

## Implementation Steps

### Step 1: Create DM Package Structure
**Files**: `lambdas/dm/__init__.py`, `lambdas/dm/prompts/__init__.py`

Create the dm package with prompts subpackage.

```python
# lambdas/dm/__init__.py
"""DM (Dungeon Master) module for AI-powered game narration."""

# lambdas/dm/prompts/__init__.py
"""Prompt building utilities for the DM."""
from .context import DMPromptBuilder
from .system_prompt import build_system_prompt
from .rules import BECMI_RULES
from .campaigns import CAMPAIGN_PROMPTS
from .output_format import OUTPUT_FORMAT
```

**Validation**:
- [ ] Package imports correctly
- [ ] No circular dependencies

### Step 2: Create BECMI Rules Reference
**Files**: `lambdas/dm/prompts/rules.py`

Create the BECMI rules text block (~800 tokens) covering:
- Combat mechanics (attack rolls, AC, damage)
- Ability modifiers table
- Saving throws by class
- Class abilities (Fighter, Thief, Magic-User, Cleric)
- Thief skills table
- XP requirements
- Healing rules

Use the exact text from init-05-dm-system-prompt.md Section 2.

**Validation**:
- [ ] Rules text is accurate to BECMI
- [ ] Modifier table matches shared/utils.py calculate_modifier()

### Step 3: Create Campaign Prompts
**Files**: `lambdas/dm/prompts/campaigns.py`

Create campaign-specific prompt text for each setting:
- `default` - Classic adventure (The Rusty Tankard, Millbrook)
- `dark_forest` - Survival horror (haunted elven forest)
- `cursed_castle` - Gothic horror (Castle Ravenmoor, vampire lord)
- `forgotten_mines` - Dungeon crawl (Deepholm mines)

Each includes setting description, tone, and opening scenario.

**Validation**:
- [ ] All 4 campaigns defined
- [ ] Matches CampaignSetting enum from shared/campaigns.py

### Step 4: Create Output Format Instructions
**Files**: `lambdas/dm/prompts/output_format.py`

Create the output format instructions (~400 tokens) that define:
- Two-part response structure (narrative + JSON)
- StateChanges JSON schema
- Dice rolls format
- Combat state format
- Rules for when to include each field

Use the exact format from init-05-dm-system-prompt.md Section 3.

**Validation**:
- [ ] JSON examples are valid
- [ ] Field names match models.py

### Step 5: Create System Prompt Builder
**Files**: `lambdas/dm/prompts/system_prompt.py`

Build the complete cacheable system prompt by combining:
1. DM Identity (~300 tokens)
2. BECMI Rules (~800 tokens)
3. Output Format (~400 tokens)
4. Content Guidelines (~200 tokens)
5. Campaign Setting (~200 tokens)

```python
def build_system_prompt(campaign: str = "default") -> str:
    """Build the complete cacheable system prompt."""
    return "\n\n".join([
        DM_IDENTITY,
        BECMI_RULES,
        OUTPUT_FORMAT,
        CONTENT_GUIDELINES,
        CAMPAIGN_PROMPTS.get(campaign, CAMPAIGN_PROMPTS["default"]),
    ])
```

**Validation**:
- [ ] Total ~2000 tokens
- [ ] Campaign selection works

### Step 6: Create Dynamic Context Builder
**Files**: `lambdas/dm/prompts/context.py`

Implement `DMPromptBuilder` class with:
- `build_context()` - formats character stats and session state
- `format_character_block()` - compact character representation
- `format_world_state()` - current location and flags
- `format_message_history()` - last N messages, truncated to fit budget
- `build_user_message()` - wraps player action

```python
def format_character_block(character: Character) -> str:
    """Format character for context (~150 tokens)."""
    # Calculate modifiers using shared/utils.py
    stats = character.stats
    return f"""## CURRENT CHARACTER
Name: {character.name}
Class: {character.character_class.value} Level {character.level}
HP: {character.hp}/{character.max_hp}
Gold: {character.gold} gp
XP: {character.xp}

Abilities: STR {stats.strength} ({calculate_modifier(stats.strength):+d}), ...

Inventory: {', '.join(character.inventory) or 'Empty'}"""
```

**Validation**:
- [ ] Imports Character, Session from shared/models.py
- [ ] Uses calculate_modifier from shared/utils.py

### Step 7: Create Response Parser
**Files**: `lambdas/dm/parser.py`

Implement response parsing:
- Extract narrative text before JSON block
- Find and parse ```json blocks using regex
- Validate against Pydantic models
- Handle parsing failures gracefully (return narrative only)

```python
import re
from .models import DMResponse, StateChanges

JSON_BLOCK_PATTERN = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)

def parse_dm_response(response_text: str) -> DMResponse:
    """Parse Claude's response into structured data."""
    # Find JSON block
    match = JSON_BLOCK_PATTERN.search(response_text)

    if match:
        narrative = response_text[:match.start()].strip()
        json_str = match.group(1)
        try:
            data = json.loads(json_str)
            return DMResponse(
                narrative=narrative,
                state_changes=StateChanges(**data.get("state_changes", {})),
                dice_rolls=[DiceRoll(**r) for r in data.get("dice_rolls", [])],
                combat_active=data.get("combat_active", False),
                enemies=[Enemy(**e) for e in data.get("enemies", [])],
            )
        except (json.JSONDecodeError, ValidationError):
            pass

    # Fallback: return narrative only
    return DMResponse(narrative=response_text.strip())
```

**Validation**:
- [ ] Handles valid JSON correctly
- [ ] Handles missing JSON gracefully
- [ ] Handles malformed JSON gracefully

### Step 8: Create Response Models
**Files**: `lambdas/dm/models.py`

Implement all Pydantic models from Technical Specification:
- StateChanges
- DiceRoll
- Enemy
- DMResponse

Add model_config for JSON serialization if needed.

**Validation**:
- [ ] All fields have defaults where appropriate
- [ ] Models serialize to JSON correctly

### Step 9: Write Unit Tests for Prompt Builders
**Files**: `lambdas/tests/test_dm_prompts.py`

Test cases:
- `test_build_system_prompt_default` - builds with default campaign
- `test_build_system_prompt_each_campaign` - all 4 campaigns work
- `test_system_prompt_contains_sections` - all sections present
- `test_format_character_block` - character formatting
- `test_format_world_state` - world state formatting
- `test_format_message_history` - message history formatting
- `test_format_message_history_truncation` - truncates long history
- `test_build_user_message` - action formatting

**Validation**:
- [ ] >80% coverage of prompts/
- [ ] All tests pass

### Step 10: Write Unit Tests for Parser
**Files**: `lambdas/tests/test_dm_parser.py`

Test cases:
- `test_parse_valid_response` - full response with JSON
- `test_parse_state_changes` - all state change fields
- `test_parse_dice_rolls` - dice roll extraction
- `test_parse_combat_state` - combat_active and enemies
- `test_parse_no_json` - response without JSON block
- `test_parse_invalid_json` - malformed JSON fallback
- `test_parse_partial_state_changes` - missing optional fields

**Validation**:
- [ ] >80% coverage of parser.py
- [ ] All tests pass

### Step 11: Lint and Validate
**Files**: All new files

Run linting and type checking:
```bash
cd lambdas && ruff check dm/ --fix
cd lambdas && mypy dm/
```

**Validation**:
- [ ] No lint errors
- [ ] No type errors
- [ ] All imports resolve

### Step 12: Integration Test with Mock Response
**Files**: `lambdas/tests/test_dm_integration.py`

Create an integration test that:
1. Builds a complete system prompt
2. Builds context with mock character and session
3. Simulates a Claude response with narrative and JSON
4. Parses the response
5. Verifies state changes are extracted correctly

```python
def test_full_dm_flow():
    """Integration test: prompt building → response parsing."""
    builder = DMPromptBuilder()

    # Build prompts
    system = builder.build_system_prompt("dark_forest")
    context = builder.build_context(mock_character, mock_session)
    user_msg = builder.build_user_message("I attack the goblin")

    # Simulate Claude response
    mock_response = '''
The goblin snarls as you swing your sword...

```json
{
  "state_changes": {"hp_delta": -3, "xp_delta": 25},
  "dice_rolls": [{"type": "attack", "roll": 15, "modifier": 2, "total": 17, "success": true}],
  "combat_active": true
}
```'''

    # Parse
    result = parse_dm_response(mock_response)

    assert result.state_changes.hp_delta == -3
    assert result.state_changes.xp_delta == 25
    assert len(result.dice_rolls) == 1
    assert result.combat_active is True
```

**Validation**:
- [ ] Integration test passes
- [ ] Full flow works end-to-end

---

## Testing Requirements

### Unit Tests
- Prompt builder constructs valid prompts for all campaigns
- Character block formats correctly with all stat combinations
- Message history truncates at token limit
- Parser extracts JSON from valid responses
- Parser handles missing/malformed JSON gracefully
- All models validate and serialize correctly

### Integration Tests
- Full flow: build prompts → parse mock response → extract state changes
- Token count stays within budget (~3100 input tokens)

### Manual Testing
1. Run prompts through token counter to verify budget
2. Test sample responses from Claude (init-06 will enable this)

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites
- Backend deployed: `cd cdk && cdk deploy --all`
- Prompts module importable: `python -c "from dm.prompts import DMPromptBuilder"`
- Tests passing: `cd lambdas && pytest tests/test_dm_*.py -v`

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Import DMPromptBuilder | No import errors | ☐ |
| 2 | Build system prompt for "default" | Returns ~2000 token string | ☐ |
| 3 | Build system prompt for all 4 campaigns | All return valid strings | ☐ |
| 4 | Build context with mock character/session | Returns ~800 token string | ☐ |
| 5 | Parse valid JSON response | State changes extracted | ☐ |
| 6 | Parse response without JSON | Returns narrative only | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Invalid campaign | build_system_prompt("invalid") | Falls back to default | ☐ |
| Malformed JSON | JSON with syntax error | Returns narrative only | ☐ |
| Empty response | "" | Returns empty DMResponse | ☐ |

### Browser Checks
N/A - This is backend-only (no frontend changes)

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| JSONDecodeError | Malformed JSON in response | Return narrative only, log warning |
| ValidationError | JSON doesn't match schema | Return narrative only, log warning |
| KeyError | Missing campaign | Fall back to "default" campaign |

### Edge Cases
- Very long message history: Truncate to fit token budget (last N messages)
- Empty inventory: Display "Empty" instead of empty list
- Missing character stats: Use defaults (9-12 = +0 modifier)
- Claude returns no JSON block: Return narrative only, empty state changes

---

## Cost Impact

### Claude API
- No API calls in this PRP (prompts only, no handler yet)
- Estimated per-action cost when used: ~$0.001
  - Cached input (2000 tokens): $0.25/M × 0.1 = $0.00005
  - Dynamic input (1100 tokens): $0.25/M = $0.000275
  - Output (500 tokens): $1.25/M = $0.000625

### AWS
- No new AWS resources
- Lambda code size increase: ~20KB
- Estimated monthly impact: $0

---

## Open Questions

1. **Token counting**: Should we implement token counting now or defer to init-06?
   - Recommendation: Defer - not needed until actual API calls

2. **Message history limit**: 10 or 15 messages for history?
   - Recommendation: Start with 10, can increase if token budget allows

3. **Fallback behavior**: When JSON parsing fails, should we retry or just continue?
   - Recommendation: Continue with narrative only, log warning for monitoring

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Very detailed spec, clear prompt structure |
| Feasibility | 10 | No blockers, follows existing patterns |
| Completeness | 9 | All sections covered, integration test included |
| Alignment | 10 | Matches ADRs, within budget, uses Haiku |
| **Overall** | **9.5** | High confidence, well-defined scope |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
