# init-16-inventory-fixes

## Overview

Fix bugs discovered in manual testing of PRP-15 inventory system. Item removal doesn't work, quantities display incorrectly, and the inventory button scrolls out of view.

## Dependencies

- init-15-inventory-system (COMPLETE)

## Problems Discovered

### 1. Item Removal Not Working

**Symptom**: Player drops items ("I give my dagger to the fighter") → DM outputs `-dagger` in state changes → Item remains in inventory.

**Root Cause**: The `inventory_remove` logic in `_apply_state_changes` uses exact string matching:
```python
if (item["name"] if isinstance(item, dict) else item) != item_name
```

But:
- DM outputs lowercase: `dagger`
- Inventory stores title case: `Dagger`
- No match → no removal

**Fix**: Implement case-insensitive matching for removals, similar to how `find_item_by_name()` handles additions.

### 2. Quantity Display Issues

**Symptom**: All items show "x1" regardless of actual quantity. Rations should show actual count (e.g., "x7" for a week's worth).

**Root Cause**: 
- Starting equipment sets `quantity: 1` for everything including rations
- UI may not be reading quantity correctly from item data

**Fix**: 
- Set correct starting quantities (rations: 7, torches: 3)
- Ensure UI displays actual quantity from item.quantity
- When using stackable items, decrement quantity instead of removing

### 3. Inventory Button Scrolls Away

**Symptom**: When chat history grows, scrolling down hides the inventory toggle button. Player loses access to inventory during gameplay.

**Fix**: Make the character status bar (HP/XP/Gold/Level + Inventory toggle) sticky/fixed at the top of the game area.

## Proposed Solutions

### Solution 1: Case-Insensitive Item Removal

In `lambdas/dm/service.py`, update the removal logic:

```python
def _find_inventory_item_index(inventory: list, item_name: str) -> int | None:
    """Find item index by name (case-insensitive)."""
    normalized = item_name.lower().strip()
    for i, item in enumerate(inventory):
        if isinstance(item, dict):
            if item.get("name", "").lower() == normalized:
                return i
            if item.get("item_id", "").lower() == normalized:
                return i
    return None

# In _apply_state_changes:
for item_name in state.inventory_remove:
    idx = _find_inventory_item_index(inventory, item_name)
    if idx is not None:
        item = inventory[idx]
        qty = item.get("quantity", 1) if isinstance(item, dict) else 1
        if qty > 1:
            inventory[idx]["quantity"] = qty - 1
        else:
            inventory.pop(idx)
    else:
        logger.warning(f"Tried to remove item not in inventory: {item_name}")
```

### Solution 2: Correct Starting Quantities

In `lambdas/shared/items.py`, update ITEM_CATALOG and starting equipment:

```python
# Update rations definition
"rations": ItemDefinition(
    id="rations", name="Rations", item_type=ItemType.CONSUMABLE,
    uses=7, value=5,  # 7 days worth
    description="A week's worth of trail rations."
),

# Update torch definition  
"torch": ItemDefinition(
    id="torch", name="Torch", item_type=ItemType.MISC,
    value=1,
    description="Provides light for about an hour."
),
```

In character creation, set appropriate quantities:
```python
# When adding starting equipment
quantity = 7 if item_id == "rations" else (3 if item_id == "torch" else 1)
inventory.append({
    "item_id": item_id,
    "name": item_def.name,
    "quantity": quantity,
    ...
})
```

### Solution 3: Sticky Character Status Bar

In frontend, make the status bar fixed/sticky:

```tsx
// CharacterStatus or GamePage layout
<div className="sticky top-0 z-10 bg-gray-900 border-b border-gray-700">
  {/* HP, XP, Gold, Level display */}
  {/* Inventory toggle button */}
</div>
```

## Out of Scope

- New item types or catalog additions
- Combat USE_ITEM improvements (working correctly)
- Shop/merchant system

## Acceptance Criteria

- [ ] Dropping "dagger" removes "Dagger" from inventory (case-insensitive match)
- [ ] Dropping "Dagger" removes "Dagger" from inventory (exact match still works)
- [ ] Using item with quantity > 1 decrements quantity instead of removing
- [ ] Rations start with quantity 7, display as "Rations x7"
- [ ] Torches start with quantity 3, display as "Torch x3"
- [ ] Inventory button visible at all times regardless of scroll position
- [ ] Warning logged when trying to remove non-existent item

## Testing Plan

### Unit Tests
- `test_inventory_remove_case_insensitive` - "dagger" removes "Dagger"
- `test_inventory_remove_by_item_id` - "potion_healing" removes potion
- `test_inventory_remove_decrements_quantity` - qty 7 → 6
- `test_inventory_remove_at_quantity_one` - qty 1 → item removed
- `test_starting_equipment_quantities` - rations=7, torch=3

### Manual Integration Tests
1. Create new character → verify rations show "x7"
2. Say "I eat one ration" → verify rations show "x6"
3. Say "I drop my dagger" → verify dagger removed from inventory
4. Scroll down in chat → verify inventory button still visible
5. Open inventory while scrolled → verify panel displays correctly

## Cost Impact

None - bug fixes only, no additional API calls or storage.

## Notes

These fixes follow the established patterns:
- Case-insensitive matching mirrors `find_item_by_name()` for consistency
- Quantity handling enables proper resource management gameplay
- Sticky UI is standard UX pattern for persistent controls
