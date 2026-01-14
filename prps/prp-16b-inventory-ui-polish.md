# PRP-16b: Inventory UI Polish

**Created**: 2026-01-14
**Initial**: `initials/init-16b-inventory-ui-polish.md`
**Status**: Ready

---

## Overview

### Problem Statement

PRP-16a testing confirmed item removal and quantity sync work. Three remaining issues discovered:

1. **Quantity display format**: Items show `Sword ... x7` with quantity pushed to far right edge. Want inline format like `Sword (7)` next to name, and only if quantity > 1.

2. **Character status bar clipped**: The `sticky top-0` on CharacterStatus combined with `overflow-hidden` on GamePage root is causing the status bar to be partially cut off or not rendering correctly.

3. **Item acquisition not working**: When player picks up dropped item or receives loot, items don't appear in inventory. Need to diagnose whether backend is rejecting or frontend isn't syncing.

### Proposed Solution

1. **Fix quantity display** in `InventoryPanel.tsx` - change from `flex justify-between` with quantity on right to inline display with parentheses.

2. **Fix status bar clipping** - remove conflicting `sticky top-0` from CharacterStatus since it's already in a flex-shrink-0 container. Ensure the header wrapper has appropriate background and doesn't clip.

3. **Debug item acquisition** - check CloudWatch logs for inventory add attempts, verify `find_item_by_name()` works, and potentially add increment logic for adding items already in inventory.

### Success Criteria

- [ ] Item quantities display inline: `Rations (4)` not `Rations ... x4`
- [ ] Single items show no quantity badge: `Sword` not `Sword (1)` or `Sword ... x1`
- [ ] Consumables still show quantity and Use button in combat
- [ ] Character status bar (name, level, HP, XP, Gold) fully visible - not clipped
- [ ] Scrolling chat doesn't affect status bar visibility
- [ ] Picking up a dropped item adds it back to inventory
- [ ] Receiving loot from DM adds items to inventory

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Inventory data model
- `prps/prp-16a-frontend-inventory-sync.md` - Previous fix (COMPLETE)
- `prps/prp-16-inventory-fixes.md` - Backend fixes (COMPLETE)

### Dependencies

- Required: PRP-16a (frontend inventory sync) - COMPLETE
- Required: PRP-16 (backend inventory fixes) - COMPLETE

### Files to Modify

```
frontend/src/components/game/InventoryPanel.tsx  # Fix quantity display format
frontend/src/components/game/CharacterStatus.tsx # Remove sticky (handled by parent)
frontend/src/pages/GamePage.tsx                  # Ensure no clipping
lambdas/dm/service.py                            # Fix inventory_add for existing items
```

---

## Technical Specification

### Quantity Display Changes

**Current** (InventoryPanel.tsx):
```tsx
<div className="flex justify-between items-center">
  <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
  {item.quantity > 1 && (
    <span className="text-gray-500 text-xs">x{item.quantity}</span>
  )}
</div>
```

**New**:
```tsx
<div className="flex items-center">
  <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
  {item.quantity > 1 && (
    <span className="text-gray-500 text-xs ml-1">({item.quantity})</span>
  )}
</div>
```

For consumables, keep the same pattern but ensure the Use button stays on the right:
```tsx
<div className="flex items-center justify-between">
  <div className="flex items-center">
    <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
    {item.quantity > 1 && (
      <span className="text-gray-500 text-xs ml-1">({item.quantity})</span>
    )}
  </div>
  {inCombat && onUseItem && item.item_id && (
    <button ...>Use</button>
  )}
</div>
```

### Status Bar Layout Fix

**Current** (CharacterStatus.tsx line 45):
```tsx
<div className="bg-gray-800 border-b border-gray-700 px-4 py-3 sticky top-0 z-20">
```

**New** - Remove sticky positioning (parent already handles fixed header):
```tsx
<div className="bg-gray-800 border-b border-gray-700 px-4 py-3">
```

The parent in GamePage.tsx already has `flex-shrink-0` which keeps the header fixed at top.

### Item Acquisition Fix

**Current Issue**: When adding an item that was dropped, the code checks `if item_def.id not in inventory_ids` and only adds if NOT present. But if player dropped a sword, it IS removed from inventory, so re-adding should work...

**Actual Issue Found**: The code works correctly for items not in inventory. But there's no increment logic - if player already has 1 torch and picks up another torch, it doesn't increment. We should add increment logic:

**New** (dm/service.py around line 1338):
```python
for item_name in state.inventory_add:
    item_def = find_item_by_name(item_name)
    if item_def is None:
        logger.warning(f"DM tried to give unknown item: {item_name}")
        continue

    # Check if item already in inventory
    existing_idx = None
    for i, inv_item in enumerate(inventory):
        if isinstance(inv_item, dict) and inv_item.get("item_id") == item_def.id:
            existing_idx = i
            break

    if existing_idx is not None:
        # Increment quantity of existing item
        inventory[existing_idx]["quantity"] = inventory[existing_idx].get("quantity", 1) + 1
        logger.info(f"Incremented {item_def.name} quantity")
    else:
        # Add new item
        inventory.append({
            "item_id": item_def.id,
            "name": item_def.name,
            "quantity": 1,
            "item_type": item_def.item_type.value,
            "description": item_def.description,
        })
        logger.info(f"Added item to inventory: {item_def.name}")
```

---

## Implementation Steps

### Step 1: Fix Quantity Display Format

**Files**: `frontend/src/components/game/InventoryPanel.tsx`

Update all 4 item type sections (equipment, consumables, quest items, other) to use inline quantity format.

For equipment, quest items, and other:
```tsx
<div className="flex items-center">
  <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
  {item.quantity > 1 && (
    <span className="text-gray-500 text-xs ml-1">({item.quantity})</span>
  )}
</div>
```

For consumables (need Use button on right):
```tsx
<div className="flex items-center justify-between">
  <div className="flex items-center">
    <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
    {item.quantity > 1 && (
      <span className="text-gray-500 text-xs ml-1">({item.quantity})</span>
    )}
  </div>
  {inCombat && onUseItem && item.item_id && (
    <button
      onClick={() => onUseItem(item.item_id!)}
      className="px-2 py-0.5 text-xs bg-green-600 hover:bg-green-500 rounded text-white"
    >
      Use
    </button>
  )}
</div>
```

**Validation**:
- [ ] Frontend builds without errors
- [ ] Quantities show inline: `Rations (7)` not `Rations ... x7`
- [ ] Single items show no quantity: `Sword` not `Sword (1)`
- [ ] Consumables still show Use button in combat

### Step 2: Fix Character Status Bar Layout

**Files**: `frontend/src/components/game/CharacterStatus.tsx`

Remove `sticky top-0 z-20` from the root div - the parent in GamePage.tsx already handles fixed positioning via `flex-shrink-0`.

```tsx
// Change from:
<div className="bg-gray-800 border-b border-gray-700 px-4 py-3 sticky top-0 z-20">

// To:
<div className="bg-gray-800 border-b border-gray-700 px-4 py-3">
```

**Validation**:
- [ ] Status bar fully visible (name, level, HP bar, XP, Gold)
- [ ] No clipping at top of viewport
- [ ] Scrolling chat doesn't affect status bar

### Step 3: Fix Item Acquisition (Increment Existing)

**Files**: `lambdas/dm/service.py`

Update `_apply_state_changes` to increment quantity when adding an item that already exists in inventory.

Replace the current `inventory_add` loop (around line 1328-1351) with logic that:
1. Checks if item already exists in inventory
2. If exists: increment quantity
3. If not exists: add new item

```python
for item_name in state.inventory_add:
    # Validate item through catalog lookup
    item_def = find_item_by_name(item_name)
    if item_def is None:
        logger.warning(
            f"DM tried to give unknown item: {item_name}",
            extra={"item_name": item_name},
        )
        continue  # Skip unknown items

    # Check if item already in inventory
    existing_idx = None
    for i, inv_item in enumerate(inventory):
        if isinstance(inv_item, dict) and inv_item.get("item_id") == item_def.id:
            existing_idx = i
            break

    if existing_idx is not None:
        # Increment quantity of existing item
        current_qty = inventory[existing_idx].get("quantity", 1)
        inventory[existing_idx]["quantity"] = current_qty + 1
        logger.info(
            f"Incremented {item_def.name} quantity to {current_qty + 1}",
            extra={"item_id": item_def.id},
        )
    else:
        # Add new item
        inventory.append({
            "item_id": item_def.id,
            "name": item_def.name,
            "quantity": 1,
            "item_type": item_def.item_type.value,
            "description": item_def.description,
        })
        logger.info(
            f"Added item to inventory: {item_def.name}",
            extra={"item_id": item_def.id, "item_type": item_def.item_type.value},
        )
```

**Validation**:
- [ ] All backend tests pass
- [ ] CloudWatch shows "Added item" or "Incremented" logs
- [ ] Picking up dropped item adds it back

### Step 4: Run Tests and Deploy

**Files**: All modified files

```bash
# Backend tests
cd lambdas && .venv/bin/pytest -q

# Frontend tests and build
cd frontend && npm test -- --run && npm run build

# Deploy backend
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip

# Bump version and deploy frontend
# Update version in package.json to 0.13.3
npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] Backend tests pass
- [ ] Frontend builds
- [ ] Deployed to prod

---

## Testing Requirements

### Unit Tests

No new unit tests required - existing tests cover the functionality. Just verify they still pass.

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
| 1 | Load game page with existing character | Status bar fully visible - name, level, HP bar, XP, Gold all showing | ☐ |
| 2 | Open inventory panel | Items display with inline quantities: `Rations (7)` | ☐ |
| 3 | Check equipment section | Sword shows no quantity badge (just `Sword`) | ☐ |
| 4 | Type "I drop my sword" | Sword removed from inventory | ☐ |
| 5 | Type "I pick up the sword" | Sword appears back in inventory | ☐ |
| 6 | Type "I pick up a torch from the ground" | Torch count increments (3 → 4) | ☐ |
| 7 | Scroll chat history down | Status bar stays fully visible, not clipped | ☐ |
| 8 | Start combat, check consumables | Use button appears next to potions | ☐ |

### Debug Verification

Check CloudWatch for item addition logs:
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/chaos-prod-dm" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern '"Added item"' \
  --query 'events[*].message' \
  --output text
```

### Browser Checks

- [ ] No JavaScript errors in Console
- [ ] No layout shift when scrolling
- [ ] Status bar doesn't flicker or get cut off
- [ ] Inventory quantities display correctly (no `x` prefix)

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Unknown item | DM mentions item not in catalog | Log warning, skip silently |
| Null inventory | Character data corrupted | Handled by `get("inventory", [])` |

### Edge Cases

- Empty inventory: Shows "Your pack is empty" message
- All items quantity 1: No quantity badges shown
- Very long item names: Handled by flex layout

---

## Cost Impact

### Claude API

- No change - same AI calls

### AWS

- No new resources
- Estimated impact: $0

---

## Open Questions

None - requirements are clearly defined from user testing.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Clear visual issues with specific fixes |
| Feasibility | 10 | Simple CSS and logic changes |
| Completeness | 9 | All reported issues addressed |
| Alignment | 10 | Polish fixes, no budget impact |
| **Overall** | **9.75** | High confidence - straightforward fixes |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-16a)
- [x] Success criteria are measurable
