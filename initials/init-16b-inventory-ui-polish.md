# init-16b-inventory-ui-polish

## Overview

Fix remaining issues discovered in PRP-16a testing. Item removal and quantity sync now working. Remaining issues are UI polish and item acquisition.

## Dependencies

- init-16a-frontend-inventory-sync (COMPLETE)

## Confirmed Working

- ✅ Item removal syncs to UI (dropped sword disappeared)
- ✅ Quantity decrement works (dropped 3 rations, showed 4 remaining)
- ✅ Inventory toggle visible when scrolling

## Problems

### 1. Quantity Display Format
**Current**: Item name on left, quantity `x7` pushed to far right edge of the line
**Wanted**: Inline format like `Rations (7)` next to the item name

### 2. Character Status Bar Cut Off
The sticky header fix caused the character name, level, HP, XP, and Gold to be partially cut off or clipped at the top of the viewport.

### 3. Item Acquisition Not Working
When player picks up a dropped item or DM gives items, they don't appear in inventory. 
- Player dropped sword, couldn't pick it back up
- Need to check if backend is rejecting or if frontend isn't syncing additions

## Proposed Solutions

### Fix 1: Inline Quantity Display

Update `InventoryPanel.tsx` to show quantity inline next to item name:

```tsx
// Current - quantity pushed to right edge
<div className="flex justify-between">
  <span>{item.name}</span>
  <span className="text-gray-500">x{item.quantity}</span>
</div>

// New - inline format next to name
<div>
  <span>{item.name}</span>
  {item.quantity > 1 && (
    <span className="text-gray-500 ml-1">({item.quantity})</span>
  )}
</div>
```

Only show quantity if > 1 (no need to show "(1)" for single items like Sword).

### Fix 2: Character Status Bar Layout

The `overflow-hidden` on the parent container is clipping the status bar. Need to restructure so:
- Status bar is never clipped
- Only the chat area scrolls

Check `CharacterStatus.tsx` and `GamePage.tsx` for any conflicting overflow or height constraints.

### Fix 3: Item Acquisition

The backend validates items via `find_item_by_name()` before adding. When player says "I pick up the sword", the DM should output `+Sword` in state changes.

**Debug steps for Claude Code:**
1. Check CloudWatch for "DM tried to give unknown item" warnings
2. Verify `find_item_by_name("sword")` returns the Sword item (case-insensitive)
3. Verify `find_item_by_name("Sword")` works too
4. If backend adds successfully, verify frontend syncs `inventory` from response

**Likely issue**: The `inventory_add` code path might not be using the same case-insensitive matching as removal, OR the frontend isn't syncing additions properly.

## Acceptance Criteria

- [ ] Item quantities display inline: `Rations (4)` not `Rations ... x4`
- [ ] Single items show no quantity: `Sword` not `Sword (1)`
- [ ] Character status bar (name, level, HP, XP, Gold) fully visible - not clipped
- [ ] Scrolling chat doesn't clip the status bar
- [ ] Picking up a dropped item adds it back to inventory
- [ ] DM giving item (loot, reward) adds it to inventory
- [ ] CloudWatch shows successful item additions

## Files to Modify

```
frontend/src/components/game/InventoryPanel.tsx  # Quantity format
frontend/src/pages/GamePage.tsx                  # Status bar layout fix
frontend/src/components/game/CharacterStatus.tsx # Check for clipping issues
lambdas/dm/service.py                            # Debug/fix inventory_add path if needed
```

## Debugging Steps for Claude Code

Before implementing fixes, run diagnostics:

1. **Check CloudWatch for item add attempts:**
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/chaos-prod-dm" \
  --start-time $(date -d '2 hours ago' +%s)000 \
  --filter-pattern '"inventory"' \
  --query 'events[*].message' \
  --output text | head -50
```

2. **Verify find_item_by_name works for "sword":**
   - Check if the function is being called for `inventory_add` items
   - Check if case-insensitive matching works for additions (it works for removals)

3. **Check if DM is even outputting +Sword:**
   - Look at raw DM responses in logs
   - The DM might be narrating the pickup but not including state changes

## Testing Plan

### Manual Tests
1. Create character → verify status bar fully visible (name, HP, XP, Gold, Level)
2. Open inventory → verify quantities show inline: `Rations (7)`
3. Drop sword → verify sword removed
4. Say "I pick up the sword" → verify sword added back to inventory
5. Scroll chat → verify status bar stays fully visible
6. Enter combat, loot enemy → verify loot appears in inventory

## Cost Impact

$0 - Primarily frontend CSS/layout changes, minor backend debugging

## Notes

Item removal is confirmed working (16a success). Item addition uses similar code path but may have different validation logic that's failing silently.
