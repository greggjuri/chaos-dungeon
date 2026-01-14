# init-16d-layout-and-tools

## Overview

Fix the two remaining issues from PRP-16c testing:
1. Status bar completely disappears when scrolling (layout regression)
2. Tool items like "shovel" not being added to inventory

## Dependencies

- init-16c-final-inventory-fixes (COMPLETE)

## Problems

### 1. Status Bar Disappears When Scrolling

**Before 16c**: Status bar was clipped at top but partially visible
**After 16c**: Status bar completely disappears when scrolling chat

The `h-screen` change made the entire page scrollable instead of just the chat area. Need to ensure:
- The header (status bar + inventory toggle) is **fixed** at the top
- Only the chat history area scrolls
- The action input stays fixed at the bottom

### 2. "Shovel" Not in Keywords

Player bought a shovel (`+shovel` in state changes) but it wasn't added because "shovel" isn't in QUEST_KEYWORDS. Need to add common tool keywords.

## Proposed Solutions

### Fix 1: Proper Fixed Header Layout

The layout needs three sections:
1. **Fixed header** - CharacterStatus + InventoryToggle (never scrolls)
2. **Scrollable middle** - ChatHistory (only this scrolls)
3. **Fixed footer** - ActionInput (never scrolls)

```tsx
<div className="h-screen flex flex-col bg-gray-900">
  {/* FIXED HEADER - flex-shrink-0 keeps it from compressing */}
  <header className="flex-shrink-0 bg-gray-900 border-b border-gray-700">
    <CharacterStatus ... />
    <InventoryToggle ... />
    {showInventory && <InventoryPanel ... />}
  </header>
  
  {/* SCROLLABLE MIDDLE - flex-1 + overflow-y-auto */}
  <main className="flex-1 overflow-y-auto">
    <ChatHistory ... />
  </main>
  
  {/* FIXED FOOTER - flex-shrink-0 keeps it from compressing */}
  <footer className="flex-shrink-0 bg-gray-800 border-t border-gray-700">
    <ActionInput ... />
  </footer>
</div>
```

Key points:
- Parent is `h-screen flex flex-col`
- Header and footer have `flex-shrink-0`
- Middle has `flex-1 overflow-y-auto` (this is the ONLY scrollable area)
- No `overflow-hidden` on parent (that was causing issues)

### Fix 2: Add Tool Keywords

Add common tools to QUEST_KEYWORDS:

```python
# Tools
"shovel", "pickaxe", "axe", "hoe", "hammer", "saw", "chisel", 
"tongs", "pliers", "wrench", "screwdriver", "crowbar", "lever",
"rake", "broom", "mop", "brush", "sponge",
```

## Acceptance Criteria

- [ ] Status bar (name, level, HP, XP, Gold) **always visible** at top
- [ ] Inventory toggle **always visible** below status bar
- [ ] Only chat history scrolls when content overflows
- [ ] Action input **always visible** at bottom
- [ ] Buying/finding tools (shovel, pickaxe, etc.) adds them to inventory

## Files to Modify

```
frontend/src/pages/GamePage.tsx    # Fix layout structure
lambdas/shared/items.py            # Add tool keywords
```

## Testing Plan

1. Load game → status bar fully visible
2. Send multiple actions to fill chat
3. Scroll chat → status bar stays fixed at top
4. Scroll chat → action input stays fixed at bottom
5. Buy a shovel → shovel appears in inventory

## Cost Impact

$0 - Layout CSS and keyword additions only
