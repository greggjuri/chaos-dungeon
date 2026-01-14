# init-16e-layout-hotfix

## Overview

Emergency hotfix for layout regression in PRP-16d, plus inventory panel UX improvement.

## Problems

### 1. Header Scrolls Off-Screen
After 16d, the header (status bar, inventory) is not fixed - it scrolls with the chat. Users see the bottom of chat on load and must scroll up to see their character info.

**Root cause**: Removing `overflow-hidden` from the root container made the entire page scrollable instead of containing scroll within ChatHistory.

### 2. Inventory Panel Too Small
The inventory panel has `max-h-48` (192px) which requires scrolling to see all items. Users want:
- Larger default size to see more items
- Ability to drag/resize the panel height

## Solutions

### Fix 1: Layout Structure

The layout needs THREE non-scrolling sections with ONE scrolling section:

```tsx
<div className="h-screen flex flex-col bg-gray-900 overflow-hidden">
  {/* FIXED: Header - flex-shrink-0 prevents compression */}
  <header className="flex-shrink-0">
    <CharacterStatus />
    <InventoryToggle />
    {showInventory && <InventoryPanel />}
  </header>

  {/* SCROLLABLE: Chat - flex-1 takes remaining space, overflow-y-auto enables scroll */}
  <div className="flex-1 overflow-y-auto">
    <ChatHistory />
  </div>

  {/* FIXED: Combat/Death UI - flex-shrink-0 */}
  {combat && <CombatUI className="flex-shrink-0" />}
  {characterDead && <DeathScreen className="flex-shrink-0" />}

  {/* FIXED: Action input - flex-shrink-0 */}
  <ActionInput className="flex-shrink-0" />
</div>
```

**Key points:**
1. Root has `overflow-hidden` to contain all scrolling
2. Header has `flex-shrink-0` to stay at top
3. Chat wrapper has `flex-1 overflow-y-auto` - this is the ONLY scrollable element
4. Footer elements have `flex-shrink-0` to stay at bottom

### Fix 2: Resizable Inventory Panel

Replace fixed `max-h-48` with a resizable panel:

```tsx
const [inventoryHeight, setInventoryHeight] = useState(200); // Default 200px

// Inventory panel with drag handle
{showInventory && (
  <div 
    className="bg-gray-800/80 border-b border-gray-700 overflow-y-auto"
    style={{ height: `${inventoryHeight}px`, maxHeight: '50vh' }}
  >
    <InventoryPanel items={inventoryItems} ... />
    
    {/* Drag handle at bottom */}
    <div 
      className="h-2 bg-gray-700 cursor-ns-resize hover:bg-amber-600 transition-colors"
      onMouseDown={handleDragStart}
    />
  </div>
)}
```

Drag handler:
```tsx
const handleDragStart = (e: React.MouseEvent) => {
  e.preventDefault();
  const startY = e.clientY;
  const startHeight = inventoryHeight;
  
  const handleMouseMove = (moveEvent: MouseEvent) => {
    const delta = moveEvent.clientY - startY;
    const newHeight = Math.max(100, Math.min(startHeight + delta, window.innerHeight * 0.5));
    setInventoryHeight(newHeight);
  };
  
  const handleMouseUp = () => {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};
```

**Constraints:**
- Minimum height: 100px
- Maximum height: 50vh (half the viewport)
- Default height: 200px (was 192px / max-h-48)

## Files to Modify

```
frontend/src/pages/GamePage.tsx
```

## Acceptance Criteria

### Layout
- [ ] On page load, header (name, HP, XP, Gold) is visible at top
- [ ] Scrolling chat does NOT move the header
- [ ] Scrolling chat does NOT move the action input
- [ ] Chat auto-scrolls to bottom (newest messages visible)

### Inventory Panel
- [ ] Default height ~200px (shows more items than before)
- [ ] Drag handle visible at bottom of inventory panel
- [ ] Dragging handle resizes panel height
- [ ] Minimum height 100px, maximum 50vh
- [ ] Panel contents scroll if items exceed panel height

## Testing

1. Load game → header visible immediately
2. Send messages → header stays fixed
3. Scroll chat → header and input stay fixed
4. Open inventory → larger panel, more items visible
5. Drag inventory handle down → panel grows
6. Drag inventory handle up → panel shrinks (min 100px)

## Cost Impact

$0 - CSS and React state only
