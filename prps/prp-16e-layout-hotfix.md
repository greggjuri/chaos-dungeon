# PRP-16e: Layout Hotfix and Resizable Inventory

**Created**: 2026-01-14
**Initial**: `initials/init-16e-layout-hotfix.md`
**Status**: Ready

---

## Overview

### Problem Statement

PRP-16d introduced a layout regression by removing `overflow-hidden` from the root container. This causes the entire page to scroll instead of containing scrolling within ChatHistory. Users see the bottom of chat on load and the header scrolls away.

Additionally, the inventory panel is limited to `max-h-48` (192px) which requires scrolling to see all items.

### Proposed Solution

1. **Layout Fix**: Add back `overflow-hidden` to the root container to properly contain scrolling within the flex child that has `overflow-y-auto`.

2. **Resizable Inventory**: Replace fixed `max-h-48` with a draggable resize handle that allows users to adjust the inventory panel height between 100px and 50vh.

### Success Criteria
- [ ] Header (status bar, inventory toggle) **always visible** at top
- [ ] Scrolling chat does **not** move the header
- [ ] Action input **always visible** at bottom
- [ ] Chat auto-scrolls to bottom showing newest messages
- [ ] Inventory panel default height ~200px
- [ ] Drag handle visible at bottom of inventory panel
- [ ] Panel resizable between 100px min and 50vh max

---

## Context

### Related Documentation
- `prps/prp-16d-layout-and-tools.md` - Previous attempt (introduced regression)
- `prps/prp-16c-final-inventory-fixes.md` - Earlier layout work

### Dependencies
- PRP-16d (Complete) - Tool keywords are already merged

### Files to Modify
```
frontend/src/pages/GamePage.tsx    # Fix layout, add resizable inventory
```

---

## Technical Specification

### Layout Fix Analysis

**Current Code** (broken):
```tsx
<div className="flex flex-col h-screen bg-gray-900">
  <header className="flex-shrink-0">...</header>
  <ChatHistory ... />  {/* Has flex-1 overflow-y-auto */}
  <ActionInput className="flex-shrink-0" />
</div>
```

**Problem**: Without `overflow-hidden` on the root, the browser allows the entire flex container to scroll, not just the ChatHistory.

**Fixed Code**:
```tsx
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
  <header className="flex-shrink-0">...</header>
  <ChatHistory ... />  {/* Has flex-1 overflow-y-auto */}
  <ActionInput className="flex-shrink-0" />
</div>
```

### Resizable Inventory Panel

Add state and drag handler:

```tsx
const [inventoryHeight, setInventoryHeight] = useState(200);

const handleInventoryDragStart = useCallback((e: React.MouseEvent) => {
  e.preventDefault();
  const startY = e.clientY;
  const startHeight = inventoryHeight;

  const handleMove = (moveEvent: MouseEvent) => {
    const delta = moveEvent.clientY - startY;
    const newHeight = Math.max(100, Math.min(startHeight + delta, window.innerHeight * 0.5));
    setInventoryHeight(newHeight);
  };

  const handleUp = () => {
    document.removeEventListener('mousemove', handleMove);
    document.removeEventListener('mouseup', handleUp);
  };

  document.addEventListener('mousemove', handleMove);
  document.addEventListener('mouseup', handleUp);
}, [inventoryHeight]);
```

UI structure:
```tsx
{showInventory && (
  <div
    className="bg-gray-800/80 border-b border-gray-700 overflow-y-auto relative"
    style={{ height: `${inventoryHeight}px` }}
  >
    <InventoryPanel items={inventoryItems} ... />
    {/* Drag handle */}
    <div
      className="absolute bottom-0 left-0 right-0 h-2 bg-gray-700 cursor-ns-resize hover:bg-amber-600 transition-colors"
      onMouseDown={handleInventoryDragStart}
    />
  </div>
)}
```

---

## Implementation Steps

### Step 1: Fix Root Container Overflow
**Files**: `frontend/src/pages/GamePage.tsx`

Add `overflow-hidden` back to the root container.

**Change**:
```tsx
// Line 114: Change from
<div className="flex flex-col h-screen bg-gray-900">

// To
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
```

**Validation**:
- [ ] Header stays fixed when scrolling chat
- [ ] Chat scrolls within its container

### Step 2: Add Inventory Height State
**Files**: `frontend/src/pages/GamePage.tsx`

Add state for inventory panel height and the drag handler.

Add to imports:
```tsx
import { useState, useCallback } from 'react';
// useCallback already imported, just add the handler
```

Add after `showInventory` state:
```tsx
const [inventoryHeight, setInventoryHeight] = useState(200);
```

Add handler after `getInventoryItems`:
```tsx
// Handle inventory panel resize
const handleInventoryDragStart = useCallback((e: React.MouseEvent) => {
  e.preventDefault();
  const startY = e.clientY;
  const startHeight = inventoryHeight;

  const handleMove = (moveEvent: MouseEvent) => {
    const delta = moveEvent.clientY - startY;
    const newHeight = Math.max(100, Math.min(startHeight + delta, window.innerHeight * 0.5));
    setInventoryHeight(newHeight);
  };

  const handleUp = () => {
    document.removeEventListener('mousemove', handleMove);
    document.removeEventListener('mouseup', handleUp);
  };

  document.addEventListener('mousemove', handleMove);
  document.addEventListener('mouseup', handleUp);
}, [inventoryHeight]);
```

**Validation**:
- [ ] Component compiles without errors

### Step 3: Update Inventory Panel UI
**Files**: `frontend/src/pages/GamePage.tsx`

Replace the fixed `max-h-48` inventory panel with the resizable version.

**Change** the inventory panel section (currently lines 131-140):
```tsx
{/* Collapsible inventory panel */}
{showInventory && (
  <div
    className="bg-gray-800/80 border-b border-gray-700 overflow-y-auto relative"
    style={{ height: `${inventoryHeight}px` }}
  >
    <InventoryPanel
      items={inventoryItems}
      inCombat={combatActive || (combat?.active ?? false)}
      onUseItem={handleUseItem}
    />
    {/* Drag handle for resizing */}
    <div
      className="absolute bottom-0 left-0 right-0 h-2 bg-gray-700 cursor-ns-resize hover:bg-amber-600 transition-colors"
      onMouseDown={handleInventoryDragStart}
    />
  </div>
)}
```

**Validation**:
- [ ] Inventory panel renders at 200px height
- [ ] Drag handle visible at bottom
- [ ] Dragging resizes panel

### Step 4: Run Tests and Deploy
**Files**: N/A

```bash
# Frontend tests
cd frontend && npm test -- --run

# Bump version
# Edit frontend/package.json: "version": "0.13.6"

# Build and deploy
cd frontend && npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] All tests pass
- [ ] Version bumped to 0.13.6
- [ ] Frontend deployed
- [ ] CloudFront invalidated

---

## Testing Requirements

### Unit Tests
- Existing tests should pass (no API changes)

### Manual Testing
1. Load game → header visible at top immediately
2. Send multiple actions → chat fills with messages
3. Scroll chat → header stays fixed at top
4. Scroll chat → action input stays fixed at bottom
5. Open inventory → panel appears at 200px height
6. Drag handle down → panel grows (up to 50vh max)
7. Drag handle up → panel shrinks (down to 100px min)
8. Panel contents scroll if items exceed height

---

## Integration Test Plan

### Prerequisites
- Frontend deployed to S3
- CloudFront cache invalidated
- Browser DevTools open

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Load game page | Header (name, HP, Gold) visible at top | ☐ |
| 2 | Send 5+ actions | Chat fills with messages | ☐ |
| 3 | Scroll chat down | Header stays fixed at top | ☐ |
| 4 | Scroll chat down | Action input stays fixed at bottom | ☐ |
| 5 | Click "Inventory" | Panel opens at ~200px height | ☐ |
| 6 | Drag handle down | Panel grows larger | ☐ |
| 7 | Drag to max | Panel stops at 50vh | ☐ |
| 8 | Drag handle up | Panel shrinks | ☐ |
| 9 | Drag to min | Panel stops at 100px | ☐ |
| 10 | Scroll chat with inventory open | Header + inventory stay fixed | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] No layout shifts during scroll
- [ ] Drag handle cursor changes to `ns-resize`

---

## Error Handling

### Edge Cases
- **Empty chat**: Header and footer visible, empty middle area
- **Many items**: Inventory panel scrolls internally when items exceed height
- **Window resize**: 50vh max adjusts dynamically to new viewport height
- **Rapid dragging**: Event listeners properly cleaned up on mouseup

---

## Cost Impact

### Claude API
- $0 - No AI changes

### AWS
- $0 - CSS and React state changes only

---

## Open Questions

None - the root cause is clear and the solution is straightforward.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Root cause identified, clear fix |
| Feasibility | 10 | Standard CSS/React patterns |
| Completeness | 9 | Both issues fully addressed |
| Alignment | 10 | Pure bugfix + UX improvement, $0 cost |
| **Overall** | 9.75 | Very high confidence |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling covers edge cases
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-16d)
- [x] Success criteria are measurable
