# PRP-16a: Frontend Inventory Sync

**Created**: 2026-01-14
**Initial**: `initials/init-16a-frontend-inventory-sync.md`
**Status**: Ready

---

## Overview

### Problem Statement

Inventory changes from the server aren't reflected in the UI. The backend correctly removes/updates items (confirmed via CloudWatch logs showing "Removed Sword from inventory"), but the frontend state doesn't sync:

1. **Root Cause**: The backend's `CharacterSnapshot` only contains `inventory: list[str]` (item names), but the frontend's `getInventoryItems()` uses `character.inventory: Item[]` (full objects with quantity, type, etc.). The `character` state is only loaded once on mount and never updated from action responses.

2. **Secondary Issue**: The sticky header fix from PRP-16 isn't working - the inventory toggle still scrolls out of view.

### Proposed Solution

1. **Enhance CharacterSnapshot** to include full `Item` objects instead of just strings. This allows the frontend to sync the complete inventory state after each action.

2. **Update frontend** to sync `character.inventory` from the action response, not just `characterSnapshot`.

3. **Fix sticky header** by restructuring the layout to use proper overflow containment.

### Success Criteria

- [ ] Dropping an item removes it from UI inventory immediately
- [ ] Using a consumable decrements quantity in UI (e.g., Rations x7 → x6)
- [ ] Picking up an item adds it to UI inventory immediately
- [ ] Inventory toggle button always visible at top of game area
- [ ] Inventory panel opens correctly when header is sticky

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Data models, inventory is `list[Item]`
- `docs/DECISIONS.md` - No inventory-specific ADRs
- `prps/prp-16-inventory-fixes.md` - Backend fixes (COMPLETE)
- `prps/prp-15-inventory-system.md` - Original implementation

### Dependencies

- Required: PRP-16 (backend inventory fixes) - COMPLETE
- Required: PRP-15 (server-side inventory system) - COMPLETE

### Files to Modify

```
lambdas/dm/models.py               # Update CharacterSnapshot.inventory to list[Item]
lambdas/dm/service.py              # Build full Item objects for snapshot (3 places)
frontend/src/types/index.ts        # Update CharacterSnapshot type
frontend/src/hooks/useGameSession.ts # Sync character.inventory from response
frontend/src/pages/GamePage.tsx    # Fix sticky header layout
```

---

## Technical Specification

### Data Model Changes

**Current Backend `CharacterSnapshot`:**
```python
class CharacterSnapshot(BaseModel):
    hp: int
    max_hp: int
    xp: int
    gold: int
    level: int
    inventory: list[str]  # Just names: ["Sword", "Rations"]
```

**New Backend `CharacterSnapshot`:**
```python
class CharacterSnapshot(BaseModel):
    hp: int
    max_hp: int
    xp: int
    gold: int
    level: int
    inventory: list[Item]  # Full objects with quantity, type, etc.
```

**Current Frontend `CharacterSnapshot`:**
```typescript
interface CharacterSnapshot {
  hp: number;
  max_hp: number;
  xp: number;
  gold: number;
  level: number;
  inventory: string[];  // Just names
}
```

**New Frontend `CharacterSnapshot`:**
```typescript
interface CharacterSnapshot {
  hp: number;
  max_hp: number;
  xp: number;
  gold: number;
  level: number;
  inventory: Item[];  // Full objects
}
```

### Frontend State Sync Logic

**Current (broken):**
```typescript
// useGameSession.ts - only updates snapshot, not character
setCharacterSnapshot(response.character);

// GamePage.tsx - uses character (never updated)
const getInventoryItems = (): Item[] => {
  return character.inventory;  // Stale after first load!
};
```

**New (fixed):**
```typescript
// useGameSession.ts - update both snapshot and character inventory
setCharacterSnapshot(response.character);
setCharacter(prev => prev ? {
  ...prev,
  hp: response.character.hp,
  max_hp: response.character.max_hp,
  xp: response.character.xp,
  gold: response.character.gold,
  level: response.character.level,
  inventory: response.character.inventory,  // Now has full Item objects
} : null);
```

### Sticky Header Fix

The current `flex-shrink-0` approach doesn't create proper scroll containment. The fix is to ensure the scrollable area (`ChatHistory`) has proper overflow settings while the header stays fixed.

**Current structure:**
```tsx
<div className="flex flex-col h-[calc(100vh-4rem)]">
  <div className="flex-shrink-0">  {/* Header - but parent doesn't contain scroll! */}
    <CharacterStatus />
    <InventoryToggle />
  </div>
  <ChatHistory />  {/* This needs overflow-y-auto */}
</div>
```

**Fixed structure:**
```tsx
<div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
  <div className="flex-shrink-0 bg-gray-900 z-10">
    <CharacterStatus />
    <InventoryToggle />
    {showInventory && <InventoryPanel />}
  </div>
  <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
    <ChatHistory />  {/* Already has internal scroll */}
  </div>
</div>
```

Key: `min-h-0` on flex child allows it to shrink below content size, enabling scroll.

---

## Implementation Steps

### Step 1: Update Backend CharacterSnapshot Model

**Files**: `lambdas/dm/models.py`

Import Item and update CharacterSnapshot:

```python
# At top of file, ensure Item is imported
from shared.items import Item

# Update CharacterSnapshot
class CharacterSnapshot(BaseModel):
    """Character state to include in response."""

    hp: int
    """Current hit points."""

    max_hp: int
    """Maximum hit points."""

    xp: int
    """Current experience points."""

    gold: int
    """Current gold."""

    level: int
    """Character level."""

    inventory: list[Item]
    """List of items in inventory."""
```

**Validation**:
- [ ] Model compiles without errors
- [ ] Existing tests still pass (may need adjustment)

### Step 2: Update Backend Service to Build Full Inventory

**Files**: `lambdas/dm/service.py`

Replace the three `inventory_names` list comprehensions with full Item objects. There are 3 places where `CharacterSnapshot` is built:

1. Line ~582-625 (exploration response)
2. Line ~773-836 (use_item response)
3. Line ~1010-1096 (combat response)

Replace pattern:
```python
# OLD
inventory_names = [
    item["name"] if isinstance(item, dict) else item
    for item in character.get("inventory", [])
]
# ...
character=CharacterSnapshot(
    ...
    inventory=inventory_names,
)

# NEW
from shared.items import Item

inventory_items = [
    Item(**item) if isinstance(item, dict) else Item(name=item, quantity=1, item_type="misc")
    for item in character.get("inventory", [])
]
# ...
character=CharacterSnapshot(
    ...
    inventory=inventory_items,
)
```

**Validation**:
- [ ] All tests pass
- [ ] Lint passes (`ruff check`)
- [ ] Manual test: action response includes full item objects

### Step 3: Update Frontend CharacterSnapshot Type

**Files**: `frontend/src/types/index.ts`

Update the CharacterSnapshot interface:

```typescript
/** Character snapshot from action response */
export interface CharacterSnapshot {
  hp: number;
  max_hp: number;
  xp: number;
  gold: number;
  level: number;
  inventory: Item[];  // Changed from string[]
}
```

Also update the loadSession function's initial snapshot building since it now needs to match:

**Validation**:
- [ ] TypeScript compiles without errors
- [ ] No type errors in consuming files

### Step 4: Update useGameSession Hook

**Files**: `frontend/src/hooks/useGameSession.ts`

Update the `loadSession` function to build initial snapshot correctly (it currently maps to strings):

```typescript
// In loadSession, around line 119-126:
// OLD:
setCharacterSnapshot({
  hp: characterData.hp,
  max_hp: characterData.max_hp,
  xp: characterData.xp,
  gold: characterData.gold,
  level: characterData.level,
  inventory: characterData.inventory.map((item) => item.name),  // Wrong - was strings
});

// NEW:
setCharacterSnapshot({
  hp: characterData.hp,
  max_hp: characterData.max_hp,
  xp: characterData.xp,
  gold: characterData.gold,
  level: characterData.level,
  inventory: characterData.inventory,  // Now full Item[]
});
```

Update `sendAction` to sync character inventory from response (around line 215):

```typescript
// After setCharacterSnapshot(response.character), add:
setCharacterSnapshot(response.character);

// Sync character inventory from snapshot
setCharacter((prev) =>
  prev
    ? {
        ...prev,
        hp: response.character.hp,
        max_hp: response.character.max_hp,
        xp: response.character.xp,
        gold: response.character.gold,
        level: response.character.level,
        inventory: response.character.inventory,
      }
    : null
);
```

**Validation**:
- [ ] TypeScript compiles
- [ ] Lint passes
- [ ] Unit tests pass

### Step 5: Fix Sticky Header in GamePage

**Files**: `frontend/src/pages/GamePage.tsx`

Update the layout structure for proper scroll containment:

```tsx
return (
  <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-900 overflow-hidden">
    {/* Fixed header section - never scrolls */}
    <div className="flex-shrink-0 bg-gray-900 z-10">
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

    {/* Scrollable content area - takes remaining space */}
    <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
      {/* Chat history - scrollable middle */}
      <ChatHistory messages={messages} isLoading={isSendingAction} />

      {/* Combat UI - shown when turn-based combat is active */}
      {combat && combat.active && (
        <CombatUI
          combat={combat}
          onAction={sendCombatAction}
          isLoading={isSendingAction}
        />
      )}

      {/* ... rest of UI ... */}
    </div>

    {/* ... action input, token counter ... */}
  </div>
);
```

Key changes:
- Add `overflow-hidden` to root container
- Add `bg-gray-900 z-10` to header for proper layering
- Wrap scrollable content in `flex-1 min-h-0 overflow-hidden flex flex-col`

**Validation**:
- [ ] Frontend builds without errors
- [ ] Visual test: scroll chat and verify header stays fixed

### Step 6: Deploy and Integration Test

**Files**: Lambda + Frontend deployment

```bash
# 1. Run tests
cd lambdas && .venv/bin/pytest

# 2. Deploy backend to PROD
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip

# 3. Bump version in frontend/package.json

# 4. Build and deploy frontend
cd frontend && npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"

# 5. Commit version bump
git add . && git commit -m "feat: frontend inventory sync and sticky header fix" && git push
```

**Validation**:
- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] Integration tests pass (see below)

---

## Testing Requirements

### Unit Tests

**Backend** (`lambdas/tests/test_dm_service.py`):
- Test that `CharacterSnapshot.inventory` contains full `Item` objects
- Test that item quantities are preserved in snapshot
- Test legacy string inventory items are converted properly

**Frontend** (`frontend/src/hooks/useGameSession.test.ts`):
- Test that `character.inventory` is updated after action response
- Test initial snapshot matches character inventory
- No new tests needed for sticky header (visual test)

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
| 1 | Create new fighter character | Character created with starting equipment | ☐ |
| 2 | Start new session, open inventory | Shows Sword, Shield, Rations x7, Torch x3, etc. | ☐ |
| 3 | Type "I drop my sword" and submit | DM acknowledges, Sword disappears from inventory | ☐ |
| 4 | Type "I eat a ration" and submit | DM acknowledges, Rations shows x6 (was x7) | ☐ |
| 5 | Scroll down in chat history (add messages) | Inventory button stays visible at top | ☐ |
| 6 | Click inventory toggle while scrolled | Panel opens at top, not scrolled away | ☐ |
| 7 | Type "I pick up the sword" | If DM returns sword, it should appear in inventory | ☐ |

### Debug Verification

Open browser console and verify:
```javascript
// After dropping item, check action response in Network tab
// Response should have:
// character.inventory: [{ name: "Shield", quantity: 1, item_type: "armor", ... }, ...]
// NOT: character.inventory: ["Shield", ...]
```

### Error Scenarios

| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Drop non-existent item | "I drop my wand of fireballs" | DM handles gracefully, no crash, inventory unchanged | ☐ |
| Use last consumable | Use last torch | Torch removed entirely from inventory | ☐ |

### Browser Checks

- [ ] No JavaScript errors in Console
- [ ] No CORS errors in Console
- [ ] API responses are 2xx
- [ ] `character.inventory` in response has full Item objects (Network tab)
- [ ] Inventory panel doesn't flicker during scroll

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Legacy string inventory | Old character data | Convert to Item with default values |
| Missing item fields | Incomplete data | Use defaults (quantity=1, item_type="misc") |

### Edge Cases

- Empty inventory: Display "No items" message (already handled)
- Quantity reaches 0: Item should be removed entirely (backend handles)
- Very long inventory: max-h-48 with overflow-y-auto (already handled)

---

## Cost Impact

### Claude API

- No change - same AI calls as before

### AWS

- No new resources
- Slightly larger response payloads (Item objects vs strings)
- Estimated impact: $0 (negligible bytes difference)

---

## Open Questions

None - requirements are clearly defined from testing.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Bug with clear reproduction and root cause |
| Feasibility | 10 | Straightforward data model and state sync changes |
| Completeness | 9 | All issues addressed, comprehensive test plan |
| Alignment | 10 | Bug fix, no budget impact, follows existing patterns |
| **Overall** | **9.75** | High confidence - well-defined fix |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-15, PRP-16)
- [x] Success criteria are measurable
