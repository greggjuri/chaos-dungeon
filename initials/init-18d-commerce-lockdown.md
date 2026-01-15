# init-18d-commerce-lockdown

## Overview

Lock down remaining exploit vectors in the commerce system. Despite init-18c adding `commerce_sell` and `commerce_buy` fields, the DM continues to use `inventory_remove` and `gold_delta` directly, causing players to lose items and gold instead of gaining them during sales.

## Problem

### Observed Behavior

**Test 1: Selling shield**
- Player: "I look to acquire a gold piece for my shield"
- Expected: Shield removed, +20 gold (50% of 40)
- Actual: Shield removed, **-80 gold** (lost gold instead of gaining)

**Test 2: Selling torch**
- Player: "I want to sell one of my torches"
- Expected: Torch removed, +1 gold
- Actual: Torch removed, **-1 gold** (lost gold instead of gaining)

### Root Cause

1. **DM ignoring commerce fields**: DM outputs `inventory_remove` and `gold_delta` instead of `commerce_sell`
2. **`inventory_remove` not blocked**: Init-18a only blocked `inventory_add` and positive `gold_delta`
3. **Negative `gold_delta` allowed**: We allowed negative gold for "spending", but DM misuses it
4. **Commerce detection mismatch**: "acquire" triggered BUY context instead of SELL

## Solution

Apply the same lockdown pattern from init-18a to `inventory_remove` and all `gold_delta`:

1. **Block ALL `gold_delta`** (positive AND negative) from DM
2. **Block ALL `inventory_remove`** from DM
3. **Only authorized channels can modify gold/inventory**:
   - `commerce_sell` → removes item, adds gold
   - `commerce_buy` → removes gold, adds item
   - `_claim_pending_loot()` → adds gold/items from combat
   - Combat damage → HP changes (already working)

## Implementation

### 1. Block inventory_remove in service.py

In `_apply_state_changes()`, add blocking for `inventory_remove`:

```python
def _apply_state_changes(self, character: dict, session: dict, dm_response: DMResponse):
    state = dm_response.state_changes
    
    # BLOCK: DM cannot grant gold (existing from 18a)
    if state.gold_delta > 0:
        logger.warning(
            "BLOCKED: DM attempted unauthorized gold grant",
            extra={"attempted": state.gold_delta}
        )
        state.gold_delta = 0
    
    # NEW: BLOCK DM from removing gold too
    if state.gold_delta < 0:
        logger.warning(
            "BLOCKED: DM attempted unauthorized gold removal",
            extra={"attempted": state.gold_delta}
        )
        state.gold_delta = 0
    
    # BLOCK: DM cannot add items (existing from 18a)
    if state.inventory_add:
        logger.warning(
            "BLOCKED: DM attempted unauthorized item grant",
            extra={"attempted": state.inventory_add}
        )
        state.inventory_add = []
    
    # NEW: BLOCK DM from removing items too
    if state.inventory_remove:
        logger.warning(
            "BLOCKED: DM attempted unauthorized item removal",
            extra={"attempted": state.inventory_remove}
        )
        state.inventory_remove = []
    
    # Gold and inventory changes ONLY happen through:
    # 1. commerce_sell / commerce_buy (processed separately)
    # 2. _claim_pending_loot() (combat loot)
    # 3. Future: quest rewards, etc.
```

### 2. Update DM Prompts

Make it crystal clear that direct gold/inventory changes are blocked:

```
## ITEM AND GOLD AUTHORITY (UPDATED)

You do NOT control items or gold. The server handles ALL inventory and gold changes.

BLOCKED (server will ignore these):
- gold_delta (ANY value, positive OR negative)
- inventory_add (ANY items)
- inventory_remove (ANY items)

COMMERCE (the ONLY way to buy/sell):
- To sell: commerce_sell: "<item_id>"
- To buy: commerce_buy: {"item": "<item_id>", "price": <gold>}

EXAMPLES:
❌ WRONG: gold_delta: -10, inventory_remove: ["torch"]
✅ RIGHT: commerce_sell: "torch"

❌ WRONG: gold_delta: -10, inventory_add: ["sword"]  
✅ RIGHT: commerce_buy: {"item": "sword", "price": 10}

The server will execute the transaction and handle gold/inventory automatically.
Your job is to NARRATE the transaction, not execute it.
```

### 3. Simplify Commerce Detection

Remove "acquire" from BUY_PATTERNS since it's ambiguous:

```python
BUY_PATTERNS = [
    r"\bbuy\b",
    r"\bpurchase\b",
    # Removed: r"\bacquire\b" - too ambiguous ("acquire gold for my item" = sell)
    r"\bpay\s+for\b",
    r"\bget\b.*\bfrom\b.*\b(shop|merchant|vendor|store)\b",
]
```

Add more sell patterns:

```python
SELL_PATTERNS = [
    r"\bsell\b",
    r"\btrade\b.*\bfor\b.*\bgold\b",
    r"\bexchange\b.*\bfor\b.*\b(gold|coin)\b",
    r"\bpawn\b",
    r"\bget\s+(rid\s+of|gold\s+for)\b",  # "get rid of" or "get gold for"
    r"\b(give|trade)\b.*\bfor\b.*\b(gold|coin|money)\b",
]
```

### 4. Add Diagnostic Logging

Add `COMMERCE:` logging when fields are blocked:

```python
if state.gold_delta != 0:
    logger.warning(
        "COMMERCE: Blocked gold_delta - use commerce_sell/commerce_buy",
        extra={"blocked_delta": state.gold_delta}
    )
    state.gold_delta = 0

if state.inventory_remove:
    logger.warning(
        "COMMERCE: Blocked inventory_remove - use commerce_sell",
        extra={"blocked_items": state.inventory_remove}
    )
    state.inventory_remove = []
```

## Files to Modify

```
lambdas/dm/service.py              # Block inventory_remove and all gold_delta
lambdas/dm/prompts/output_format.py  # Update authority section
lambdas/shared/actions.py          # Fix commerce detection patterns
lambdas/tests/test_item_authority.py  # Add tests for new blocks
```

## Acceptance Criteria

- [ ] `gold_delta` (positive AND negative) blocked from DM
- [ ] `inventory_remove` blocked from DM
- [ ] `commerce_sell` still works (removes item, adds gold)
- [ ] `commerce_buy` still works (removes gold, adds item)
- [ ] Combat loot still works via `_claim_pending_loot()`
- [ ] Warning logs show blocked attempts
- [ ] DM prompt clearly states all direct changes are blocked

## Testing

### Manual Test: Selling
1. Find a shop
2. "I want to sell my torch"
3. Verify torch removed, gold INCREASED (not decreased)
4. Check CloudWatch for `COMMERCE:` logs showing `commerce_sell` used

### Manual Test: Buying
1. At shop with sufficient gold
2. "I want to buy a dagger"
3. Verify gold decreased, dagger added
4. Check CloudWatch for `commerce_buy` used

### Unit Tests

```python
def test_negative_gold_delta_blocked():
    """DM cannot remove gold via gold_delta."""
    state = StateChanges(gold_delta=-50)
    # After processing, gold_delta should be 0
    
def test_inventory_remove_blocked():
    """DM cannot remove items via inventory_remove."""
    state = StateChanges(inventory_remove=["torch", "shield"])
    # After processing, inventory_remove should be []

def test_commerce_sell_still_works():
    """commerce_sell properly removes item and adds gold."""
    
def test_commerce_buy_still_works():
    """commerce_buy properly removes gold and adds item."""
```

## Edge Cases

### What about HP damage?
`hp_delta` is NOT blocked. Combat damage still works normally.

### What about XP?
`xp_delta` is NOT blocked. XP gains still work normally.

### What about location changes?
`location` is NOT blocked. Movement still works normally.

### What about item usage (potions)?
`item_used` triggers server-side item consumption. This is an authorized channel.

## Summary of Blocked vs Allowed

| Field | Blocked? | Authorized Channel |
|-------|----------|-------------------|
| `gold_delta` | ✅ ALL | `commerce_sell`, `commerce_buy`, `_claim_pending_loot` |
| `inventory_add` | ✅ ALL | `commerce_buy`, `_claim_pending_loot`, starting equipment |
| `inventory_remove` | ✅ ALL | `commerce_sell`, `item_used` |
| `hp_delta` | ❌ | Direct (combat, traps, healing) |
| `xp_delta` | ❌ | Direct (combat, quests) |
| `location` | ❌ | Direct (movement) |

## Cost Impact

None - this is tightening validation, not adding features.

## Notes

This completes the item authority lockdown started in init-18a. The principle is simple:

**If the DM can directly modify it, players will exploit it.**

The only safe approach is channeling ALL resource changes through server-controlled, validated paths.
