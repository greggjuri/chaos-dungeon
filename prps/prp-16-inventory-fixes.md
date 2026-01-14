# PRP-16: Inventory System Fixes

**Created**: 2026-01-14
**Initial**: `initials/init-16-inventory-fixes.md`
**Status**: Ready

---

## Overview

### Problem Statement
Manual testing of PRP-15 (inventory system) revealed three bugs:
1. **Item removal fails** - DM outputs `-dagger` but item stays in inventory due to case mismatch
2. **Quantities incorrect** - All items show "x1" including rations/torches that should be stacked
3. **Inventory button scrolls away** - Users lose access to inventory when chat history grows

### Proposed Solution
- Fix case-insensitive item removal with quantity decrementing
- Set correct starting quantities for stackable items (rations: 7, torches: 3)
- Make character status bar and inventory toggle sticky at top

### Success Criteria
- [ ] Dropping "dagger" removes "Dagger" from inventory (case-insensitive)
- [ ] Dropping "Dagger" still works (exact match)
- [ ] Using stackable item decrements quantity instead of removing
- [ ] Rations start with quantity 7, display as "Rations x7"
- [ ] Torches start with quantity 3, display as "Torch x3"
- [ ] Inventory button stays visible at top regardless of scroll
- [ ] Warning logged when trying to remove non-existent item

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Inventory in data models
- `docs/DECISIONS.md` - No inventory-specific ADRs
- `prps/prp-15-inventory-system.md` - Original implementation

### Dependencies
- Required: PRP-15 Inventory System (COMPLETE)

### Files to Modify
```
lambdas/dm/service.py           # Fix inventory_remove logic
lambdas/shared/items.py         # Set starting quantities for rations/torches
frontend/src/pages/GamePage.tsx # Make status bar sticky
lambdas/tests/test_dm_service.py   # Add removal tests
lambdas/tests/test_items.py        # Add quantity tests
```

---

## Technical Specification

### Inventory Removal Logic (Current vs New)

**Current (buggy)**:
```python
item_item_name = item.get("name", "").lower()
# Compares against target_name which is already .lower()
# But doesn't handle quantity decrementing
if item_id != target_id and item_item_name != target_name:
    new_inventory.append(item)
```

**New (fixed)**:
```python
def _find_inventory_item_index(inventory: list, item_name: str) -> int | None:
    """Find item index by name/id (case-insensitive)."""
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

### Starting Equipment Quantities

| Item | Current Qty | New Qty | Rationale |
|------|-------------|---------|-----------|
| Rations | 1 | 7 | A week's worth per ITEM_CATALOG |
| Torch | 1 | 3 | Reasonable adventuring supply |
| All others | 1 | 1 | Non-stackable equipment |

### Frontend Layout Fix

Current layout issue: The character status bar uses `sticky top-0` but the parent container's `h-[calc(100vh-4rem)]` and flexbox layout causes the inventory toggle bar to scroll with content.

Fix: Wrap status bar + inventory toggle in a container that's outside the scrollable chat area.

---

## Implementation Steps

### Step 1: Fix Inventory Removal Logic
**Files**: `lambdas/dm/service.py`

Add helper function and replace current removal code:

```python
def _find_inventory_item_index(inventory: list, item_name: str) -> int | None:
    """Find item index by name or item_id (case-insensitive).

    Args:
        inventory: List of inventory items (dicts or strings)
        item_name: Item name or ID to find

    Returns:
        Index of item if found, None otherwise
    """
    normalized = item_name.lower().strip()
    for i, item in enumerate(inventory):
        if isinstance(item, dict):
            if item.get("name", "").lower() == normalized:
                return i
            if item.get("item_id", "").lower() == normalized:
                return i
        elif isinstance(item, str):
            if item.lower() == normalized:
                return i
    return None
```

Replace the `inventory_remove` loop in `_apply_state_changes`:

```python
for item_name in state.inventory_remove:
    idx = _find_inventory_item_index(inventory, item_name)
    if idx is not None:
        item = inventory[idx]
        if isinstance(item, dict):
            qty = item.get("quantity", 1)
            if qty > 1:
                inventory[idx]["quantity"] = qty - 1
                logger.info(f"Decremented {item_name} quantity to {qty - 1}")
            else:
                inventory.pop(idx)
                logger.info(f"Removed {item_name} from inventory")
        else:
            # Legacy string format
            inventory.pop(idx)
            logger.info(f"Removed {item_name} from inventory (legacy)")
    else:
        logger.warning(f"Tried to remove item not in inventory: {item_name}")
```

**Validation**:
- [ ] Unit tests for case-insensitive removal
- [ ] Unit tests for quantity decrementing
- [ ] Lint passes

### Step 2: Set Correct Starting Quantities
**Files**: `lambdas/shared/items.py`

Update `get_starting_equipment` to set quantities based on item type:

```python
def get_starting_equipment(character_class: str) -> list[dict]:
    """Get starting equipment for a character class.

    Args:
        character_class: One of fighter, thief, cleric, magic_user

    Returns:
        List of inventory item dicts ready for character creation
    """
    equipment_ids = STARTING_EQUIPMENT.get(character_class.lower(), [])
    inventory = []

    # Default quantities for stackable items
    STARTING_QUANTITIES = {
        "rations": 7,  # A week's worth
        "torch": 3,    # A few torches
    }

    for item_id in equipment_ids:
        if item_id in ITEM_CATALOG:
            item_def = ITEM_CATALOG[item_id]
            quantity = STARTING_QUANTITIES.get(item_id, 1)
            inventory.append({
                "item_id": item_id,
                "name": item_def.name,
                "quantity": quantity,
                "item_type": item_def.item_type.value,
                "description": item_def.description,
            })

    return inventory
```

**Validation**:
- [ ] Unit test for rations quantity = 7
- [ ] Unit test for torch quantity = 3
- [ ] All existing tests pass

### Step 3: Make Inventory Toggle Sticky
**Files**: `frontend/src/pages/GamePage.tsx`

Restructure layout to keep status bar and inventory toggle fixed:

```tsx
return (
  <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-900">
    {/* Fixed header section - never scrolls */}
    <div className="flex-shrink-0">
      {/* Character status bar */}
      <CharacterStatus character={character} snapshot={characterSnapshot} />

      {/* Inventory toggle bar */}
      <div className="bg-gray-800/50 border-b border-gray-700 px-4 py-1">
        <button
          onClick={() => setShowInventory(!showInventory)}
          className="text-amber-400 hover:text-amber-300 text-sm font-medium flex items-center gap-1"
        >
          <span>{showInventory ? '▼' : '▶'}</span>
          <span>Inventory ({inventoryItems.length})</span>
        </button>
      </div>

      {/* Collapsible inventory panel */}
      {showInventory && (
        <div className="bg-gray-800/80 border-b border-gray-700 max-h-48 overflow-y-auto">
          <InventoryPanel
            items={inventoryItems}
            inCombat={combatActive || (combat?.active ?? false)}
            onUseItem={handleUseItem}
          />
        </div>
      )}

      {/* Error toast */}
      {error && (
        <div className="mx-4 mt-2 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
          {error}
        </div>
      )}
    </div>

    {/* Scrollable chat area - takes remaining space */}
    <div className="flex-1 overflow-hidden flex flex-col">
      <ChatHistory messages={messages} isLoading={isSendingAction} />
      {/* ... combat UI, action input, etc ... */}
    </div>
  </div>
);
```

**Validation**:
- [ ] Frontend builds without errors
- [ ] Visual check: inventory button stays at top when scrolling

### Step 4: Add Unit Tests
**Files**: `lambdas/tests/test_dm_service.py`, `lambdas/tests/test_items.py`

Add tests for inventory removal:
```python
# test_dm_service.py
class TestInventoryRemoval:
    def test_remove_case_insensitive(self):
        """'dagger' should remove 'Dagger' from inventory."""

    def test_remove_by_item_id(self):
        """'potion_healing' should remove potion by ID."""

    def test_remove_decrements_quantity(self):
        """Removing from qty 7 should result in qty 6."""

    def test_remove_at_quantity_one(self):
        """Removing at qty 1 should remove the item entirely."""

    def test_remove_nonexistent_logs_warning(self):
        """Removing nonexistent item should log warning."""
```

Add tests for starting quantities:
```python
# test_items.py
def test_rations_start_with_seven():
    """Rations should have quantity 7."""
    inventory = get_starting_equipment("fighter")
    rations = next(i for i in inventory if i["item_id"] == "rations")
    assert rations["quantity"] == 7

def test_torch_starts_with_three():
    """Torch should have quantity 3."""
    inventory = get_starting_equipment("fighter")
    torch = next(i for i in inventory if i["item_id"] == "torch")
    assert torch["quantity"] == 3
```

**Validation**:
- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] Coverage maintained

### Step 5: Deploy and Test
**Files**: Lambda deployment, frontend deployment

Deploy changes:
```bash
# Backend
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip

zip -r /tmp/char-update.zip character/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-character --zip-file fileb:///tmp/char-update.zip

# Frontend
cd frontend
npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] Backend lambdas updated
- [ ] Frontend deployed
- [ ] Integration tests pass

---

## Testing Requirements

### Unit Tests
| Test | File | Description |
|------|------|-------------|
| `test_remove_case_insensitive` | test_dm_service.py | "dagger" removes "Dagger" |
| `test_remove_by_item_id` | test_dm_service.py | "potion_healing" removes by ID |
| `test_remove_decrements_quantity` | test_dm_service.py | qty 7 → 6 |
| `test_remove_at_quantity_one` | test_dm_service.py | qty 1 → removed |
| `test_remove_nonexistent_logs_warning` | test_dm_service.py | Logs warning |
| `test_rations_start_with_seven` | test_items.py | Rations qty = 7 |
| `test_torch_starts_with_three` | test_items.py | Torch qty = 3 |

### Integration Tests
See Integration Test Plan below.

---

## Integration Test Plan

### Prerequisites
- Backend deployed to prod
- Frontend deployed to prod
- Browser DevTools open (Console + Network tabs)

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Create new fighter character | Character created successfully | ☐ |
| 2 | Start new session | Session loads with starting equipment | ☐ |
| 3 | Open inventory panel | Shows items with correct quantities (Rations x7, Torch x3) | ☐ |
| 4 | Scroll down in chat history | Inventory button stays visible at top | ☐ |
| 5 | Type "I eat one ration" | DM acknowledges, Rations shows x6 | ☐ |
| 6 | Type "I drop my dagger" | DM acknowledges, Dagger removed from inventory | ☐ |
| 7 | Type "I give my torch to the goblin" | DM acknowledges, Torch count decrements | ☐ |
| 8 | Open inventory while scrolled | Panel displays correctly | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Drop non-existent item | "I drop my wand of fireballs" | DM handles gracefully, no crash | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] No CORS errors in Console
- [ ] API requests return 2xx
- [ ] Inventory panel doesn't flicker during scroll

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Item not found for removal | DM outputs item player doesn't have | Log warning, continue processing |
| Legacy string inventory item | Old character data | Handle gracefully in removal logic |

### Edge Cases
- Empty inventory: Removal does nothing, logs warning
- Zero quantity: Should not occur (item removed at qty 1)
- Negative quantity: Validated by Pydantic (ge=1)

---

## Cost Impact

### Claude API
- No change - same number of AI calls

### AWS
- No new resources
- Negligible additional DynamoDB writes (quantity updates)
- Estimated monthly impact: $0

---

## Open Questions

None - all requirements are clearly defined in the initial spec.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Bug fixes with clear reproduction steps |
| Feasibility | 10 | Simple code changes, no architecture changes |
| Completeness | 9 | All three bugs addressed with clear solutions |
| Alignment | 10 | Bug fixes, no budget impact |
| **Overall** | 9.75 | High confidence - straightforward fixes |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-15)
- [x] Success criteria are measurable
