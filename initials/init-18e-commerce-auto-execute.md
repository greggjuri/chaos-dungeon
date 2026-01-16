# init-18e-commerce-auto-execute

## Overview

The DM (Mistral Small) ignores `commerce_sell` and `commerce_buy` fields despite clear prompt instructions. It continues using `gold_delta` and `inventory_remove` which are now blocked. This leaves players unable to buy or sell anything.

Rather than fighting the model's behavior, we'll work with it: when we detect a commerce action and see blocked fields that would make sense for that action, execute the transaction automatically.

## Problem

### Current Flow (Broken)
```
Player: "I want to sell my torch"
Server: Detects sell action, sends commerce context to DM
DM: Outputs gold_delta: 1, inventory_remove: ["torch"]
Server: Blocks both fields
Result: Nothing happens, player frustrated
```

### Logs Confirm
```
COMMERCE: Sell action detected - action="I sell another torch"
COMMERCE: Blocked gold_delta - blocked_delta: 1
COMMERCE: Blocked inventory_remove - blocked_items: ["torch"]
```

The DM is trying to do the right thing with the wrong fields.

## Solution

When we block commerce-related fields during a commerce action, use the blocked data to execute the transaction:

### New Flow
```
Player: "I want to sell my torch"
Server: Detects sell action, sends commerce context to DM
DM: Outputs gold_delta: 1, inventory_remove: ["torch"]
Server: Blocks fields, BUT...
  - Detected sell action? ✓
  - inventory_remove had items? ✓ ["torch"]
  - Items exist in player inventory? ✓
  → Auto-execute: Remove torch, add 50% value as gold
Result: Transaction completes!
```

## Implementation

### 1. Capture Blocked Data Before Clearing

In `_apply_state_changes()`, save blocked values before clearing:

```python
def _apply_state_changes(self, character: dict, session: dict, dm_response: DMResponse, action: str = ""):
    state = dm_response.state_changes
    
    # Capture blocked commerce data BEFORE clearing
    blocked_gold = state.gold_delta if state.gold_delta != 0 else None
    blocked_items_add = list(state.inventory_add) if state.inventory_add else None
    blocked_items_remove = list(state.inventory_remove) if state.inventory_remove else None
    
    # Block gold_delta
    if state.gold_delta != 0:
        logger.warning("COMMERCE: Blocked gold_delta", extra={"blocked_delta": state.gold_delta})
        state.gold_delta = 0
    
    # Block inventory_add
    if state.inventory_add:
        logger.warning("COMMERCE: Blocked inventory_add", extra={"blocked_items": state.inventory_add})
        state.inventory_add = []
    
    # Block inventory_remove
    if state.inventory_remove:
        logger.warning("COMMERCE: Blocked inventory_remove", extra={"blocked_items": state.inventory_remove})
        state.inventory_remove = []
    
    # Auto-execute commerce if conditions met
    self._auto_execute_commerce(
        character=character,
        action=action,
        blocked_items_remove=blocked_items_remove,
        blocked_items_add=blocked_items_add,
        blocked_gold=blocked_gold,
    )
```

### 2. Auto-Execute Commerce Logic

```python
def _auto_execute_commerce(
    self,
    character: dict,
    action: str,
    blocked_items_remove: list[str] | None,
    blocked_items_add: list[str] | None,
    blocked_gold: int | None,
) -> dict | None:
    """Auto-execute commerce when DM uses old fields instead of commerce_* fields.
    
    This is a fallback for when the DM ignores commerce_sell/commerce_buy instructions
    and outputs gold_delta/inventory_remove instead.
    """
    from shared.actions import is_sell_action, is_buy_action
    
    result = {"sold": [], "bought": [], "gold_changed": 0}
    
    # AUTO-SELL: Detected sell action + DM tried to remove items
    if is_sell_action(action) and blocked_items_remove:
        logger.info("COMMERCE_AUTO: Attempting auto-sell", extra={
            "action": action[:100],
            "items": blocked_items_remove,
        })
        
        inventory = character.get("inventory", [])
        
        for item_name in blocked_items_remove:
            # Normalize item name to ID
            item_id = self._normalize_item_id(item_name)
            
            # Find item in inventory
            item_index = next(
                (i for i, inv_item in enumerate(inventory) 
                 if inv_item.get("item_id") == item_id),
                None
            )
            
            if item_index is not None:
                # Get item value from catalog
                from shared.items import ITEM_CATALOG
                item_def = ITEM_CATALOG.get(item_id)
                sell_price = max(1, (item_def.value // 2) if item_def else 1)
                
                # Execute sale: remove item, add gold
                inv_item = inventory[item_index]
                quantity = inv_item.get("quantity", 1)
                
                if quantity > 1:
                    inv_item["quantity"] = quantity - 1
                else:
                    inventory.pop(item_index)
                
                character["gold"] = character.get("gold", 0) + sell_price
                
                result["sold"].append({"item": item_id, "gold": sell_price})
                logger.info("COMMERCE_AUTO: Item sold", extra={
                    "item": item_id,
                    "gold": sell_price,
                    "character_gold": character["gold"],
                })
            else:
                logger.warning("COMMERCE_AUTO: Item not in inventory", extra={
                    "item": item_name,
                    "item_id": item_id,
                })
    
    # AUTO-BUY: Detected buy action + DM tried to add items + negative gold
    if is_buy_action(action) and blocked_items_add and blocked_gold and blocked_gold < 0:
        logger.info("COMMERCE_AUTO: Attempting auto-buy", extra={
            "action": action[:100],
            "items": blocked_items_add,
            "gold_cost": abs(blocked_gold),
        })
        
        current_gold = character.get("gold", 0)
        cost = abs(blocked_gold)
        
        if cost <= current_gold:
            from shared.items import ITEM_CATALOG
            
            for item_name in blocked_items_add:
                item_id = self._normalize_item_id(item_name)
                item_def = ITEM_CATALOG.get(item_id)
                
                if item_def:
                    # Deduct gold (split evenly if multiple items)
                    item_cost = cost // len(blocked_items_add)
                    character["gold"] = character.get("gold", 0) - item_cost
                    
                    # Add item to inventory
                    self._add_item_to_inventory(character, item_def)
                    
                    result["bought"].append({"item": item_id, "gold": item_cost})
                    logger.info("COMMERCE_AUTO: Item bought", extra={
                        "item": item_id,
                        "gold": item_cost,
                        "character_gold": character["gold"],
                    })
                else:
                    logger.warning("COMMERCE_AUTO: Unknown item", extra={"item": item_name})
        else:
            logger.warning("COMMERCE_AUTO: Insufficient gold", extra={
                "cost": cost,
                "gold": current_gold,
            })
    
    return result if (result["sold"] or result["bought"]) else None
```

### 3. Pass Action to _apply_state_changes

Update the call site to pass the action string:

```python
# In _process_normal_action() or wherever _apply_state_changes is called
self._apply_state_changes(character, session, dm_response, action=action)
```

## Edge Cases

### What if DM removes items player doesn't have?
- Log warning, skip that item
- Only sell items actually in inventory

### What if DM tries to sell multiple items?
- Process each item individually
- Each gets 50% value

### What about buying multiple items?
- Split the gold cost evenly among items
- Only buy items that exist in catalog

### What if DM gives wrong gold amount?
- For selling: Ignore DM's gold_delta, use 50% of catalog value
- For buying: Use DM's gold_delta as the price (trust the DM's price)

### What about the "infinite torches" problem?
- Auto-sell checks if item exists in inventory
- If player has 0 torches, sale fails silently
- No more imaginary inventory

## Files to Modify

```
lambdas/dm/service.py  # Add _auto_execute_commerce(), update _apply_state_changes()
```

## Acceptance Criteria

- [ ] Sell action + blocked inventory_remove → auto-executes sale
- [ ] Buy action + blocked inventory_add + negative gold → auto-executes purchase
- [ ] Items not in inventory are not sold
- [ ] Items not in catalog are not bought
- [ ] Insufficient gold prevents purchase
- [ ] Correct gold amounts (50% for sell, DM price for buy)
- [ ] Logs show `COMMERCE_AUTO:` prefix for auto-executed transactions

## Testing

### Manual Test: Selling
1. Start game with torches in inventory
2. Find merchant
3. "I want to sell my torch"
4. Verify: Torch removed, gold increased by correct amount (50% value)

### Manual Test: Buying
1. Have sufficient gold
2. At shop, "I want to buy a dagger"
3. Verify: Gold decreased, dagger in inventory

### Manual Test: Sell Item Not Owned
1. Have no shields in inventory
2. "I want to sell my shield"
3. Verify: Nothing happens (no crash, no phantom items)

### Unit Tests
```python
def test_auto_sell_removes_item_adds_gold():
    """Auto-sell on blocked inventory_remove during sell action."""

def test_auto_sell_ignores_missing_items():
    """Items not in inventory are not sold."""

def test_auto_buy_deducts_gold_adds_item():
    """Auto-buy on blocked inventory_add during buy action."""

def test_auto_buy_insufficient_gold():
    """Auto-buy fails if not enough gold."""
```

## Cost Impact

None - this is server-side logic, no additional AI calls.

## Notes

This is a pragmatic workaround for the DM's inability to follow `commerce_sell`/`commerce_buy` instructions. Instead of fighting the model, we interpret its intent from the blocked fields.

The key insight: **The DM is trying to do the right thing, just with the wrong mechanism.** By capturing what it tried to do before blocking, we can execute the intended action through the correct channel.

This pattern could be useful elsewhere: when the AI's intent is clear but its method is wrong, translate rather than reject.
