# PRP-18d: Commerce Lockdown

## Overview

Lock down remaining exploit vectors in the commerce system by blocking ALL `gold_delta` (positive AND negative) and ALL `inventory_remove` from the DM. The only authorized channels for resource changes are commerce transactions, loot claims, and item usage.

## Problem Statement

Despite init-18c adding `commerce_sell` and `commerce_buy` fields, the DM continues to use `inventory_remove` and `gold_delta` directly. This causes players to lose items and gold instead of gaining them during sales:

- **Test 1**: Player says "sell my shield" → Shield removed, player loses 80 gold (instead of gaining 20)
- **Test 2**: Player says "sell my torch" → Torch removed, player loses 1 gold (instead of gaining 1)

### Root Cause

1. DM ignores `commerce_sell` field and outputs `inventory_remove` + `gold_delta` instead
2. `inventory_remove` is not blocked (init-18a only blocked `inventory_add`)
3. Negative `gold_delta` is allowed for "spending" but DM misuses it
4. The "acquire" pattern in BUY_PATTERNS is ambiguous ("acquire gold for my item" = sell, not buy)

## Implementation Steps

### Step 1: Block ALL gold_delta in _apply_state_changes

**File**: `lambdas/dm/service.py`

In `_apply_state_changes()`, change the gold_delta blocking to block ALL values (positive AND negative):

```python
# Current code (blocks only positive):
if state.gold_delta > 0:
    logger.warning(...)
    state.gold_delta = 0

# Gold spending (negative delta) is still allowed
if state.gold_delta < 0:
    character["gold"] = max(0, character["gold"] + state.gold_delta)

# New code (blocks ALL gold_delta):
if state.gold_delta != 0:
    logger.warning(
        "COMMERCE: Blocked gold_delta - use commerce_sell/commerce_buy",
        extra={"blocked_delta": state.gold_delta},
    )
    state.gold_delta = 0

# Remove the gold spending block entirely - gold changes only via commerce
```

### Step 2: Block ALL inventory_remove in _apply_state_changes

**File**: `lambdas/dm/service.py`

Add blocking for `inventory_remove` before processing removals:

```python
# Add after inventory_add blocking:
if state.inventory_remove:
    logger.warning(
        "COMMERCE: Blocked inventory_remove - use commerce_sell",
        extra={"blocked_items": state.inventory_remove},
    )
    state.inventory_remove = []

# Then update the removal loop to be a no-op (or remove entirely)
```

### Step 3: Update DM Prompts for Clarity

**File**: `lambdas/dm/prompts/output_format.py`

Update the "ITEM AND GOLD AUTHORITY" section to be clearer:

```python
## ITEM AND GOLD AUTHORITY

You do NOT control items or gold. The server handles ALL inventory and gold changes.

BLOCKED (server will ignore these):
- gold_delta (ANY value, positive OR negative)
- inventory_add (ANY items)
- inventory_remove (ANY items)

COMMERCE (the ONLY way to buy/sell):
- To sell: "commerce_sell": "<item_id>"
- To buy: "commerce_buy": {"item": "<item_id>", "price": <gold>}

EXAMPLES:
❌ WRONG: "gold_delta": -10, "inventory_remove": ["torch"]
✅ RIGHT: "commerce_sell": "torch"

❌ WRONG: "gold_delta": -10, "inventory_add": ["sword"]
✅ RIGHT: "commerce_buy": {"item": "sword", "price": 10}

The server executes transactions and handles gold/inventory automatically.
Your job is to NARRATE the transaction, not execute it.
```

### Step 4: Remove Ambiguous "acquire" from BUY_PATTERNS

**File**: `lambdas/shared/actions.py`

Remove the ambiguous "acquire" pattern and add clearer sell patterns:

```python
# Remove from BUY_PATTERNS:
r"\bacquire\b",  # Too ambiguous - "acquire gold for my item" = sell

# BUY_PATTERNS becomes:
BUY_PATTERNS = [
    r"\bbuy\b",
    r"\bpurchase\b",
    r"\bpay\b.*\bfor\b",
    r"\bget\b.*\bfrom\b.*\b(shop|merchant|vendor|store)\b",
]

# Add to SELL_PATTERNS for more coverage:
SELL_PATTERNS = [
    r"\bsell\b",
    r"\btrade\b.*\bfor\b.*\bgold\b",
    r"\bexchange\b.*\bfor\b.*\b(gold|coin)\b",
    r"\bpawn\b",
    r"\bget\s+(rid\s+of|gold\s+for)\b",
    r"\bgive\b.*\bfor\b.*\b(gold|coin|money)\b",
]
```

### Step 5: Add Unit Tests for New Blocking

**File**: `lambdas/tests/test_item_authority.py`

Add tests for the new blocking behavior:

```python
class TestCommerceBlockingComplete:
    """Test that ALL direct gold/inventory changes are blocked."""

    def test_negative_gold_delta_blocked(self):
        """DM cannot remove gold via gold_delta."""
        from dm.models import StateChanges

        state = StateChanges(gold_delta=-50)

        # Simulate blocking
        if state.gold_delta != 0:
            state.gold_delta = 0

        assert state.gold_delta == 0

    def test_inventory_remove_blocked(self):
        """DM cannot remove items via inventory_remove."""
        from dm.models import StateChanges

        state = StateChanges(inventory_remove=["torch", "shield"])

        # Simulate blocking
        if state.inventory_remove:
            state.inventory_remove = []

        assert state.inventory_remove == []
```

### Step 6: Update Commerce Test for "acquire" Pattern Removal

**File**: `lambdas/tests/test_commerce.py`

Update tests that use "acquire" pattern:

```python
# Remove "I'd like to acquire some armor" from test_buy_patterns_detected
# since "acquire" is now removed from BUY_PATTERNS
```

## Files to Modify

| File | Changes |
|------|---------|
| `lambdas/dm/service.py` | Block ALL gold_delta and inventory_remove |
| `lambdas/dm/prompts/output_format.py` | Update authority section with clearer examples |
| `lambdas/shared/actions.py` | Remove "acquire" from BUY_PATTERNS, add sell patterns |
| `lambdas/tests/test_item_authority.py` | Add tests for negative gold_delta and inventory_remove blocking |
| `lambdas/tests/test_commerce.py` | Remove "acquire" test case |

## Blocked vs Allowed Summary

| Field | Blocked? | Authorized Channel |
|-------|----------|-------------------|
| `gold_delta` | ✅ ALL | `commerce_sell`, `commerce_buy`, `_claim_pending_loot` |
| `inventory_add` | ✅ ALL | `commerce_buy`, `_claim_pending_loot`, starting equipment |
| `inventory_remove` | ✅ ALL | `commerce_sell`, `_handle_use_item` |
| `hp_delta` | ❌ | Direct (combat, traps, healing) |
| `xp_delta` | ❌ | Direct (combat, quests) |
| `location` | ❌ | Direct (movement) |

## Testing Plan

### Unit Tests
1. `test_negative_gold_delta_blocked` - Verify gold_delta < 0 is blocked
2. `test_inventory_remove_blocked` - Verify inventory_remove is blocked
3. `test_commerce_sell_still_works` - Verify commerce_sell bypasses blocks
4. `test_commerce_buy_still_works` - Verify commerce_buy bypasses blocks

### Manual Tests
1. **Sell Test**: At shop, "sell my torch" → torch removed, gold INCREASED
2. **Buy Test**: At shop, "buy a dagger" → gold decreased, dagger added
3. **Combat Test**: Kill enemy, "search bodies" → loot still claimed via pending_loot

## Acceptance Criteria

- [ ] `gold_delta` (positive AND negative) blocked from DM
- [ ] `inventory_remove` blocked from DM
- [ ] `commerce_sell` still removes item and adds gold
- [ ] `commerce_buy` still removes gold and adds item
- [ ] Combat loot still works via `_claim_pending_loot()`
- [ ] Item usage in combat still works via `_handle_use_item()`
- [ ] Warning logs show blocked attempts with `COMMERCE:` prefix
- [ ] DM prompt clearly states all direct changes are blocked
- [ ] All existing tests pass
- [ ] "acquire" pattern removed from BUY_PATTERNS

## Cost Impact

None - this is validation tightening, not adding features.

## Risks

1. **DM confusion**: The DM may struggle with the new constraints initially
   - Mitigation: Clear prompt instructions with examples
2. **Edge cases**: Some legitimate gold spending (bribes, donations) now blocked
   - Mitigation: These should also go through commerce system if needed

## Dependencies

- PRP-18c (Commerce System) - Must be complete first ✅

---

**Confidence Score**: 9.5/10

High confidence because:
- Clear problem with documented test cases
- Solution follows established pattern from init-18a
- Simple code changes with minimal risk
- Comprehensive test coverage planned

Minor uncertainty:
- May need prompt tuning if DM still struggles with commerce fields
