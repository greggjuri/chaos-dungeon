# PRP-18e: Commerce Auto-Execute

## Overview

The DM (Mistral Small) ignores `commerce_sell` and `commerce_buy` fields despite clear prompt instructions. It continues using `gold_delta` and `inventory_remove` which are now blocked (PRP-18d). This leaves players unable to buy or sell anything.

**Solution**: When we detect a commerce action and see blocked fields that would make sense for that action, auto-execute the transaction using the blocked data as intent signal.

## Problem Statement

### Current Flow (Broken)
```
Player: "I want to sell my torch"
Server: Detects sell action, sends commerce context to DM
DM: Outputs gold_delta: 1, inventory_remove: ["torch"]
Server: Blocks both fields (PRP-18d)
Result: Nothing happens, player frustrated
```

### Logs Confirm
```
COMMERCE: Sell action detected - action="I sell another torch"
COMMERCE: Blocked gold_delta - blocked_delta: 1
COMMERCE: Blocked inventory_remove - blocked_items: ["torch"]
```

The DM is trying to do the right thing with the wrong fields.

## Success Criteria

- [ ] Sell action + blocked `inventory_remove` → auto-executes sale
- [ ] Buy action + blocked `inventory_add` + negative `gold_delta` → auto-executes purchase
- [ ] Items not in inventory are NOT sold (no phantom items)
- [ ] Items not in catalog are NOT bought
- [ ] Insufficient gold prevents purchase
- [ ] Correct gold amounts: 50% value for sell, DM's price for buy
- [ ] Logs show `COMMERCE_AUTO:` prefix for auto-executed transactions
- [ ] All existing tests pass

## Technical Specification

### Key Insight

The DM is trying to do the right thing, just with the wrong mechanism. By capturing what it tried to do before blocking, we can execute the intended action through the correct channel.

### Data Flow

1. DM outputs `gold_delta` and/or `inventory_add`/`inventory_remove`
2. Server captures these values BEFORE clearing them
3. Server blocks the fields (sets to 0/empty)
4. Server checks if action matches commerce patterns
5. If match: auto-execute using captured blocked data
6. If no match: blocked values are simply discarded (current behavior)

### Auto-Sell Conditions
- `is_sell_action(action)` returns True
- `blocked_items_remove` is not empty
- At least one item exists in player's inventory

### Auto-Buy Conditions
- `is_buy_action(action)` returns True
- `blocked_items_add` is not empty
- `blocked_gold` is negative (DM tried to deduct gold)
- Player has enough gold

## Implementation Steps

### Step 1: Update `_apply_state_changes` Signature

**File**: `lambdas/dm/service.py`

Add `action` parameter to enable commerce detection:

```python
def _apply_state_changes(
    self,
    character: dict,
    session: dict,
    dm_response: DMResponse,
    action: str = "",  # Add this parameter
) -> tuple[dict, dict]:
```

### Step 2: Capture Blocked Values Before Clearing

**File**: `lambdas/dm/service.py`

In `_apply_state_changes()`, save blocked values before clearing:

```python
# Capture blocked commerce data BEFORE clearing
blocked_gold = state.gold_delta if state.gold_delta != 0 else None
blocked_items_add = list(state.inventory_add) if state.inventory_add else None
blocked_items_remove = list(state.inventory_remove) if state.inventory_remove else None

# Then do the blocking (existing code)
if state.gold_delta != 0:
    logger.warning(...)
    state.gold_delta = 0
# ... etc
```

### Step 3: Add Auto-Execute Commerce Method

**File**: `lambdas/dm/service.py`

Add new method after the blocking section:

```python
def _auto_execute_commerce(
    self,
    character: dict,
    action: str,
    blocked_items_remove: list[str] | None,
    blocked_items_add: list[str] | None,
    blocked_gold: int | None,
) -> dict:
    """Auto-execute commerce when DM uses old fields instead of commerce_* fields.

    This is a fallback for when the DM ignores commerce_sell/commerce_buy instructions
    and outputs gold_delta/inventory_remove instead.

    Returns:
        Dict with "sold" (list), "bought" (list), "errors" (list)
    """
```

### Step 4: Implement Auto-Sell Logic

In `_auto_execute_commerce()`:

```python
# AUTO-SELL: Detected sell action + DM tried to remove items
if is_sell_action(action) and blocked_items_remove:
    logger.info("COMMERCE_AUTO: Attempting auto-sell", extra={
        "action": action[:100],
        "items": blocked_items_remove,
    })

    for item_name in blocked_items_remove:
        item_id = self._normalize_item_id(item_name)
        idx = self._find_inventory_item_index(character.get("inventory", []), item_id)

        if idx is not None:
            # Get sell price (50% of catalog value, minimum 1)
            item_def = ITEM_CATALOG.get(item_id)
            sell_price = max(1, (item_def.value // 2) if item_def else 1)

            # Remove item (decrement quantity or pop)
            inv_item = character["inventory"][idx]
            qty = inv_item.get("quantity", 1)
            if qty > 1:
                inv_item["quantity"] = qty - 1
            else:
                character["inventory"].pop(idx)

            # Add gold
            character["gold"] = character.get("gold", 0) + sell_price

            result["sold"].append({"item": item_id, "gold": sell_price})
            logger.info("COMMERCE_AUTO: Item sold", extra={
                "item": item_id, "gold": sell_price
            })
```

### Step 5: Implement Auto-Buy Logic

In `_auto_execute_commerce()`:

```python
# AUTO-BUY: Detected buy action + DM tried to add items + negative gold
if is_buy_action(action) and blocked_items_add and blocked_gold and blocked_gold < 0:
    logger.info("COMMERCE_AUTO: Attempting auto-buy", extra={
        "action": action[:100],
        "items": blocked_items_add,
        "gold_cost": abs(blocked_gold),
    })

    cost = abs(blocked_gold)
    current_gold = character.get("gold", 0)

    if cost <= current_gold:
        for item_name in blocked_items_add:
            item_id = self._normalize_item_id(item_name)
            item_def = ITEM_CATALOG.get(item_id)

            if item_def:
                # Deduct gold (split evenly if multiple items)
                item_cost = cost // len(blocked_items_add)
                character["gold"] = character.get("gold", 0) - item_cost

                # Add item
                self._add_item_to_inventory(character, item_def)

                result["bought"].append({"item": item_id, "gold": item_cost})
```

### Step 6: Call Auto-Execute After Blocking

**File**: `lambdas/dm/service.py`

After the blocking section in `_apply_state_changes()`:

```python
# Auto-execute commerce if conditions met
auto_result = self._auto_execute_commerce(
    character=character,
    action=action,
    blocked_items_remove=blocked_items_remove,
    blocked_items_add=blocked_items_add,
    blocked_gold=blocked_gold,
)
if auto_result.get("sold") or auto_result.get("bought"):
    logger.info("COMMERCE_AUTO: Transaction completed", extra=auto_result)
```

### Step 7: Update Call Site

**File**: `lambdas/dm/service.py`

Update the call to `_apply_state_changes()` in `_process_normal_action()` to pass `action`:

```python
# Line ~1297
character, session = self._apply_state_changes(character, session, dm_response, action=action)
```

### Step 8: Add Unit Tests

**File**: `lambdas/tests/test_commerce.py` (add new test class)

```python
class TestCommerceAutoExecute:
    """Tests for auto-execute commerce fallback."""

    def test_auto_sell_on_blocked_inventory_remove(self, dm_service, sample_character):
        """Auto-sell executes when DM uses inventory_remove during sell action."""

    def test_auto_sell_skips_missing_items(self, dm_service, sample_character):
        """Items not in inventory are not auto-sold."""

    def test_auto_buy_on_blocked_inventory_add(self, dm_service, sample_character):
        """Auto-buy executes when DM uses inventory_add during buy action."""

    def test_auto_buy_requires_sufficient_gold(self, dm_service, sample_character):
        """Auto-buy fails if player doesn't have enough gold."""

    def test_auto_buy_skips_unknown_items(self, dm_service, sample_character):
        """Items not in catalog are not auto-bought."""

    def test_no_auto_execute_without_commerce_action(self, dm_service, sample_character):
        """Blocked fields don't trigger auto-execute for non-commerce actions."""
```

## Files to Modify

| File | Changes |
|------|---------|
| `lambdas/dm/service.py` | Add `action` param, capture blocked values, add `_auto_execute_commerce()` |
| `lambdas/tests/test_commerce.py` | Add `TestCommerceAutoExecute` test class |
| `lambdas/tests/test_dm_service.py` | Update `_apply_state_changes` calls to include `action` param |

## Testing Plan

### Unit Tests
1. `test_auto_sell_on_blocked_inventory_remove` - Verify auto-sell triggers
2. `test_auto_sell_skips_missing_items` - Verify phantom items not sold
3. `test_auto_buy_on_blocked_inventory_add` - Verify auto-buy triggers
4. `test_auto_buy_requires_sufficient_gold` - Verify gold validation
5. `test_no_auto_execute_without_commerce_action` - Verify normal actions unaffected

### Manual Tests

1. **Sell Test**:
   - Start game with torches in inventory
   - Find merchant
   - "I want to sell my torch"
   - Verify: Torch removed, gold increased by correct amount

2. **Buy Test**:
   - Have sufficient gold
   - At shop, "I want to buy a dagger"
   - Verify: Gold decreased, dagger in inventory

3. **Sell Item Not Owned**:
   - Have no shields in inventory
   - "I want to sell my shield"
   - Verify: Nothing happens (no crash, no phantom items)

4. **Insufficient Gold**:
   - Have only 2 gold
   - "I want to buy a sword" (costs 10)
   - Verify: Nothing bought, gold unchanged

## Error Handling

| Scenario | Behavior |
|----------|----------|
| DM removes item not in inventory | Log warning, skip that item |
| DM adds item not in catalog | Log warning, skip that item |
| Player can't afford purchase | Log warning, no transaction |
| DM gives wrong gold amount for sell | Ignore DM's amount, use 50% of catalog value |
| DM gives wrong gold amount for buy | Use DM's gold_delta as price (trust DM) |
| Multiple items in one transaction | Process each individually |

## Cost Impact

None - this is server-side logic, no additional AI calls.

## Open Questions

None - the init spec is comprehensive and the approach is pragmatic.

## Dependencies

- PRP-18c (Commerce System) - Provides `_normalize_item_id()`, `_add_item_to_inventory()` ✅
- PRP-18d (Commerce Lockdown) - Provides the blocking behavior we're extending ✅

---

## Confidence Scores

| Dimension | Score | Notes |
|-----------|-------|-------|
| Clarity | 9/10 | Init spec is detailed with clear examples |
| Feasibility | 10/10 | Simple extension of existing blocking logic |
| Completeness | 9/10 | All edge cases documented |
| Alignment | 10/10 | Follows established patterns, no cost impact |

**Overall Confidence: 9.5/10**

This is a pragmatic workaround that works WITH the model's behavior rather than fighting it. The pattern of "capture intent before blocking, then execute correctly" could be useful for other similar issues.
