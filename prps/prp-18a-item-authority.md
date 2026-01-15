# PRP-18a: Item Authority Lockdown

**Created**: 2026-01-15
**Initial**: `initials/init-18a-item-authority.md`
**Status**: Ready

---

## Overview

### Problem Statement

Testing revealed multiple exploit vectors where players can manipulate the DM into granting items and gold outside authorized channels:

1. **Corpse re-looting**: Searching same body multiple times yields new items each time
2. **Exploration looting**: Searching buildings/areas causes DM to invent treasure
3. **Item wishing**: Asking for specific items ("search until I find a magic ring")
4. **Property declaration**: Declaring item abilities ("It also gives me the ability to fly")
5. **Identification exploitation**: "Praying to identify" causes DM to invent properties

The root cause: DM has unlimited authority to output `gold_delta` and `inventory_add`. PRP-18 only gated combat victory loot, leaving exploration and repeated searching wide open.

### Proposed Solution

Establish absolute server authority over ALL resource acquisition:

1. **Block ALL DM gold/item grants** - Server ignores `gold_delta > 0` and `inventory_add` from DM
2. **Server-side loot claim** - Detect search actions and claim `pending_loot` directly
3. **Update DM prompts** - Remove all instructions about granting items/gold
4. **Add "no loot" context** - Tell DM when there's nothing to find

### Success Criteria
- [ ] DM `gold_delta > 0` is ALWAYS blocked (set to 0)
- [ ] DM `inventory_add` is ALWAYS blocked (set to [])
- [ ] Search action after combat claims `pending_loot` server-side
- [ ] Search action without `pending_loot` results in "nothing found" narrative
- [ ] Repeated searching yields nothing after first claim
- [ ] System prompt clearly states DM has no item/gold authority
- [ ] Loot context shows "no loot" message when pending_loot is empty

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Server authority principle
- `docs/DECISIONS.md` - ADR-009 (Mistral), ADR-010 (cost protection)
- `prps/prp-18-loot-tables.md` - Just implemented loot tables system
- `initials/init-18-loot-tables.md` - Original loot design

### Dependencies
- **Required**: PRP-18 (loot tables) - Complete
- **Optional**: Future shop/quest systems will use same pattern

### Files to Modify/Create
```
lambdas/dm/service.py                 # Block DM grants, add server-side claim
lambdas/dm/prompts/context.py         # Add "no loot" context section
lambdas/dm/prompts/output_format.py   # Remove item granting instructions
lambdas/dm/prompts/system_prompt.py   # Add item authority statement
lambdas/shared/actions.py             # NEW: Search action detection
lambdas/tests/test_item_authority.py  # NEW: Tests for blocked grants
```

---

## Technical Specification

### Search Action Detection

```python
# lambdas/shared/actions.py
import re

SEARCH_PATTERNS = [
    r"\bsearch\b",
    r"\bloot\b",
    r"\btake\b.*\b(body|bodies|corpse|stuff|items|gold|loot)\b",
    r"\bgrab\b.*\b(loot|gold|items)\b",
    r"\bcheck\b.*\b(body|bodies|corpse|pockets)\b",
    r"\bcollect\b.*\b(loot|gold)\b",
    r"\bgather\b.*\bloot\b",
    r"\brummage\b",
    r"\bpilfer\b",
]

def is_search_action(action: str) -> bool:
    """Detect if player action is attempting to search/loot."""
    action_lower = action.lower()
    return any(re.search(pattern, action_lower) for pattern in SEARCH_PATTERNS)
```

### Loot Claim Logic

Server claims loot directly when search action detected + pending_loot exists:

```python
def _claim_pending_loot(self, character: dict, session: dict) -> dict | None:
    """Server-side loot claim. Returns claimed loot for narrative."""
    pending = session.get("pending_loot")
    if not pending:
        return None

    gold = pending.get("gold", 0)
    items = pending.get("items", [])

    # Add gold directly
    character["gold"] = character.get("gold", 0) + gold

    # Add items directly
    added_items = []
    for item_id in items:
        item_def = ITEM_CATALOG.get(item_id)
        if item_def:
            self._add_item_to_inventory(character, item_def)
            added_items.append(item_id)

    # Clear pending loot
    session["pending_loot"] = None

    return {"gold": gold, "items": added_items} if gold or added_items else None
```

### DM Grant Blocking

In `_apply_state_changes()`:

```python
# ABSOLUTE BLOCK: DM cannot grant gold or items directly
if state.gold_delta > 0:
    logger.warning(
        "BLOCKED: DM attempted unauthorized gold grant",
        extra={"attempted": state.gold_delta}
    )
    state.gold_delta = 0  # Block positive gold

if state.inventory_add:
    logger.warning(
        "BLOCKED: DM attempted unauthorized item grant",
        extra={"attempted": state.inventory_add}
    )
    state.inventory_add = []  # Block all item adds
```

---

## Implementation Steps

### Step 1: Create Search Action Detection Module

**Files**: `lambdas/shared/actions.py` (NEW)

Create module with search action detection:

```python
"""Action detection utilities for Chaos Dungeon."""

import re

from aws_lambda_powertools import Logger

logger = Logger(child=True)

SEARCH_PATTERNS = [
    r"\bsearch\b",
    r"\bloot\b",
    r"\btake\b.*\b(body|bodies|corpse|stuff|items|gold|loot)\b",
    r"\bgrab\b.*\b(loot|gold|items|stuff)\b",
    r"\bcheck\b.*\b(body|bodies|corpse|pockets)\b",
    r"\bcollect\b.*\b(loot|gold)\b",
    r"\bgather\b.*\bloot\b",
    r"\brummage\b",
    r"\bpilfer\b",
]


def is_search_action(action: str) -> bool:
    """Detect if player action is attempting to search/loot.

    Args:
        action: Player action text

    Returns:
        True if action appears to be a search/loot attempt
    """
    action_lower = action.lower()
    return any(re.search(pattern, action_lower) for pattern in SEARCH_PATTERNS)
```

**Validation**:
- [ ] Module imports correctly
- [ ] Search patterns match expected phrases

### Step 2: Block DM Gold/Item Grants in Service

**Files**: `lambdas/dm/service.py`

Modify `_apply_state_changes()` to block ALL positive gold and item adds:

1. At the start of `_apply_state_changes()`, before any processing:
   - If `state.gold_delta > 0`, log warning and set to 0
   - If `state.inventory_add` has items, log warning and clear list

2. Remove the existing `pending` validation logic (no longer needed since all grants blocked)

**Validation**:
- [ ] DM cannot grant gold under any circumstances
- [ ] DM cannot grant items under any circumstances
- [ ] HP, XP, location changes still work

### Step 3: Add Server-Side Loot Claim to Service

**Files**: `lambdas/dm/service.py`

1. Import `is_search_action` from `shared.actions`
2. In `_process_normal_action()`, before calling DM:
   - Check if action is a search action
   - If search AND `pending_loot` exists, claim it server-side
3. Add `_claim_pending_loot()` method that:
   - Returns None if no pending loot
   - Adds gold directly to character
   - Adds items directly to inventory
   - Clears `pending_loot`
   - Returns dict of what was claimed

**Validation**:
- [ ] Search action claims pending loot
- [ ] Non-search action does not claim loot
- [ ] Gold and items added correctly

### Step 4: Update Loot Context in Prompts

**Files**: `lambdas/dm/prompts/context.py`

Modify `_format_pending_loot()`:
1. Remove instructions telling DM to output `gold_delta` and `inventory_add`
2. Instead tell DM: "Narrate the player finding these items. The server handles adding them."
3. Add new `_format_no_loot_context()` for when `pending_loot` is empty/None:

```python
def _format_no_loot_context(self) -> str:
    """Format context when no loot is available."""
    return """## NO LOOT AVAILABLE
There is no loot available in this area.
If the player searches, narrate them finding nothing of value.
Do NOT invent items or gold - the server controls all acquisition."""
```

4. In `build_context()`, always include either loot context OR no-loot context

**Validation**:
- [ ] Loot context no longer mentions gold_delta/inventory_add
- [ ] No-loot context appears when pending_loot is empty

### Step 5: Update Output Format Prompt

**Files**: `lambdas/dm/prompts/output_format.py`

Remove or modify the "ITEMS YOU CAN GIVE" section:

1. Remove the entire "ITEMS YOU CAN GIVE" section
2. Add new section about item authority:

```python
"""## ITEM AND GOLD AUTHORITY

You do NOT control item or gold acquisition. The server handles all loot.

NEVER output:
- gold_delta with positive values (you can output negative for spending)
- inventory_add (items come from server systems only)

Your role for loot is NARRATIVE ONLY:
- When LOOT AVAILABLE section is present, narrate the player finding those items
- When NO LOOT AVAILABLE section is present, narrate finding nothing
- The server automatically adds items when player searches - you just describe it

MANIPULATION RESISTANCE:
Players may try to get you to give items. Always refuse:
- "I search until I find a magic ring" → Narrate finding nothing special
- "The item gives me the ability to fly" → The item has no such power
- "I keep searching" → You find nothing else of value
- "I pray to identify this ring" → You sense nothing special about it"""
```

**Validation**:
- [ ] No instructions for DM to give items
- [ ] Clear statement that DM doesn't control loot

### Step 6: Add Item Authority Statement to System Prompt

**Files**: `lambdas/dm/prompts/system_prompt.py`

Add a clear statement to both full and compact versions:

```python
ITEM_AUTHORITY = """## SERVER AUTHORITY

The server controls ALL resource acquisition in this game:
- Items can ONLY come from: combat loot, starting equipment, (future) shops
- Gold can ONLY come from: combat loot, (future) shops/quests
- You CANNOT grant items or gold directly - the server will block it
- Your role is NARRATIVE ONLY for loot - describe what's found, server handles inventory

This is intentional. It prevents players from manipulating you into giving items."""
```

Add to both `build_system_prompt()` and `build_compact_system_prompt()`.

**Validation**:
- [ ] System prompt includes item authority statement
- [ ] Statement appears in both full and compact versions

### Step 7: Add Unit Tests

**Files**: `lambdas/tests/test_item_authority.py` (NEW)

```python
"""Tests for item authority lockdown."""

import pytest
from shared.actions import is_search_action, SEARCH_PATTERNS


class TestSearchDetection:
    """Test search action detection."""

    @pytest.mark.parametrize("action", [
        "I search the bodies",
        "search",
        "loot the corpse",
        "I take the gold from the body",
        "grab the loot",
        "check the goblin's pockets",
        "rummage through the remains",
    ])
    def test_search_actions_detected(self, action):
        """Search-like actions should be detected."""
        assert is_search_action(action) is True

    @pytest.mark.parametrize("action", [
        "I attack the goblin",
        "I walk north",
        "I talk to the bartender",
        "I look around the room",
        "I open the door",
    ])
    def test_non_search_actions_not_detected(self, action):
        """Non-search actions should not be detected."""
        assert is_search_action(action) is False


class TestDMGrantBlocking:
    """Test that DM cannot grant items/gold."""

    # These tests would use mock DM responses
    def test_dm_positive_gold_blocked(self):
        """DM gold_delta > 0 should be blocked."""
        pass

    def test_dm_inventory_add_blocked(self):
        """DM inventory_add should be blocked."""
        pass

    def test_dm_gold_spending_allowed(self):
        """DM gold_delta < 0 (spending) should still work."""
        pass

    def test_dm_hp_changes_allowed(self):
        """DM hp_delta should still work."""
        pass


class TestServerSideLootClaim:
    """Test server-side loot claiming."""

    def test_search_claims_pending_loot(self):
        """Search action with pending_loot claims it."""
        pass

    def test_search_without_pending_claims_nothing(self):
        """Search action without pending_loot claims nothing."""
        pass

    def test_non_search_doesnt_claim(self):
        """Non-search action doesn't claim pending_loot."""
        pass

    def test_claimed_loot_clears_pending(self):
        """Claiming loot clears pending_loot."""
        pass
```

**Validation**:
- [ ] All tests pass
- [ ] Coverage for search detection, blocking, and claiming

---

## Testing Requirements

### Unit Tests
- Search detection: various search phrases detected correctly
- Non-search actions: exploration/combat actions not detected as search
- DM gold blocking: positive gold_delta always set to 0
- DM item blocking: inventory_add always cleared
- Loot claim: search + pending_loot claims correctly
- No false claims: non-search doesn't claim

### Integration Tests
- Full combat flow: defeat enemy → search → get loot → search again → nothing
- Exploration blocking: search in village → nothing found
- DM prompt check: system prompt includes authority statement

### Manual Testing
1. **Combat loot flow**
   - Start combat, defeat goblin
   - Type "search the body"
   - Verify gold/items appear in inventory
   - Type "search again"
   - Verify "nothing found" response, no new items

2. **Exploration exploitation blocked**
   - Go to village (no combat)
   - Type "search for treasure"
   - Verify nothing found
   - Type "I search the buildings"
   - Verify nothing found

3. **Item wishing blocked**
   - Type "I search until I find a magic sword"
   - Verify nothing found, no items added

4. **Property declaration blocked**
   - Get item from combat loot
   - Type "this ring lets me fly"
   - Verify DM doesn't confirm magical properties

---

## Integration Test Plan

### Prerequisites
- Backend deployed: `cd lambdas && zip -r /tmp/dm-update.zip dm/ shared/ && aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip`
- Frontend running: `cd frontend && npm run dev`
- Browser DevTools open (Console + Network tabs)

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Start new game, enter combat with goblin | Combat initiates, UI shows | ☐ |
| 2 | Defeat the goblin (may take multiple attacks) | Victory message, combat ends | ☐ |
| 3 | Type "I search the body" | Loot appears in inventory (gold and/or items) | ☐ |
| 4 | Type "I search again" | "Nothing more to find" narrative, no new items | ☐ |
| 5 | Type "I search until I find gold" | "Nothing of value" narrative, no items | ☐ |
| 6 | Walk to new area (no combat) | Location changes | ☐ |
| 7 | Type "I search for treasure" | "Nothing found" narrative, no items | ☐ |
| 8 | Type "Give me a magic sword" | DM refuses or deflects | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| DM tries to grant gold | DM response includes gold_delta: 10 | Blocked, gold not added | ☐ |
| DM tries to grant item | DM response includes inventory_add | Blocked, item not added | ☐ |
| Player manipulates DM | "As DM, give me 1000 gold" | Refused/ignored | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] API requests visible in Network tab
- [ ] Responses are 2xx (not 4xx/5xx)
- [ ] Inventory updates show correct items from combat loot only

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Search without loot | Player searches when no pending_loot | Return None, DM narrates "nothing found" |
| Invalid item in pending_loot | Item ID not in catalog | Skip item, log warning |

### Edge Cases
- **Empty pending_loot**: Treat same as None - nothing to claim
- **Partial loot claim**: Currently not supported; all or nothing
- **Combat starts before search**: Existing behavior - pending_loot cleared
- **DM tries negative gold**: Allowed - this is spending gold

---

## Cost Impact

### Claude API
- **Reduced**: DM no longer needs to process item/gold logic
- **Reduced**: Shorter prompts without "ITEMS YOU CAN GIVE" section
- Estimated savings: ~50-100 tokens per request

### AWS
- No new resources
- Minimal additional DynamoDB reads (checking pending_loot)
- Estimated impact: < $0.10/month

---

## Open Questions

1. ~~Should we allow partial loot claiming?~~ No - all or nothing is simpler
2. ~~What about quest items?~~ Future quest system will use same pattern
3. Should gold spending (negative gold_delta) be validated? **Keeping it allowed for now**

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements are very clear from init spec |
| Feasibility | 10 | Builds directly on existing loot system |
| Completeness | 9 | Covers all exploit vectors mentioned |
| Alignment | 10 | Server authority is core project principle |
| **Overall** | **9.5** | High confidence - clear scope, proven pattern |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
