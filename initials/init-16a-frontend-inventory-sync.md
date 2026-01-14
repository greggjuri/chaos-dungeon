# init-16a-frontend-inventory-sync

## Overview

Fix frontend bug where inventory changes from the server aren't reflected in the UI. Backend correctly removes/updates items, but frontend state doesn't sync.

## Dependencies

- init-16-inventory-fixes (COMPLETE - backend working)

## Problem

**Evidence from testing:**
- Player dropped sword → DM showed `-Sword` in state changes
- CloudWatch logs confirm: `"Removed Sword from inventory"` at 15:23:16
- But UI still shows sword in inventory panel

**Root Cause:** The frontend receives updated `character.inventory` in the action response but doesn't update its local state with the new inventory array.

## Secondary Issue

The sticky header fix from PRP-16 isn't working correctly - inventory toggle still gets cut off when scrolling.

## Proposed Solutions

### Fix 1: Sync Inventory from Action Response

In the action response handler (likely in `useGameSession` hook or `GamePage`), ensure inventory is updated:

```typescript
// When processing action response
const handleActionResponse = (response: ActionResponse) => {
  // Update character snapshot (HP, XP, Gold, etc.)
  setCharacterSnapshot(response.character);
  
  // CRITICAL: Also update inventory from response
  if (response.character.inventory) {
    setInventoryItems(response.character.inventory);
  }
};
```

The issue is likely that `character.inventory` exists in the response but the frontend maintains a separate `inventoryItems` state that isn't being updated.

### Fix 2: Proper Sticky Header

The current `flex-shrink-0` approach isn't working. Use a more robust fixed positioning:

```tsx
// GamePage layout structure
<div className="h-[calc(100vh-4rem)] flex flex-col">
  {/* Fixed header - position: sticky with explicit height */}
  <div className="sticky top-0 z-20 bg-gray-900">
    <CharacterStatus ... />
    <div className="border-b border-gray-700 px-4 py-2">
      <button>Inventory ({items.length})</button>
    </div>
    {showInventory && <InventoryPanel ... />}
  </div>
  
  {/* Scrollable content area */}
  <div className="flex-1 overflow-y-auto">
    <ChatHistory ... />
  </div>
  
  {/* Fixed footer - action input */}
  <div className="flex-shrink-0">
    <ActionInput ... />
  </div>
</div>
```

Key: The parent container needs `overflow: hidden` or specific height constraints for `sticky` to work.

## Acceptance Criteria

- [ ] Dropping an item removes it from UI inventory immediately
- [ ] Using a consumable decrements quantity in UI
- [ ] Inventory toggle button always visible at top of game area
- [ ] Inventory panel opens correctly when header is sticky

## Testing Plan

### Manual Tests
1. Create character → verify starting inventory displayed
2. Say "I drop my sword" → verify sword disappears from inventory panel
3. Say "I eat a ration" → verify ration count decrements (x7 → x6)
4. Scroll chat down → verify inventory button stays visible
5. Click inventory while scrolled → verify panel opens at top

### Debug Verification
Add console.log to verify response contains updated inventory:
```typescript
console.log('Action response inventory:', response.character.inventory);
```

## Files to Modify

```
frontend/src/pages/GamePage.tsx      # Fix inventory state sync + sticky layout
frontend/src/hooks/useGameSession.ts # Ensure inventory updates from response (if separate)
```

## Cost Impact

$0 - Frontend-only changes

## Notes

This is a classic React state sync issue. The server is working correctly (confirmed via CloudWatch logs), so this is purely a frontend state management fix.
