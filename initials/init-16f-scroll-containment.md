# init-16f-scroll-containment

## Overview

Fix the scroll containment issue. The header exists but scrolls away because ChatHistory's scroll isn't properly contained.

## Problem

With `overflow-hidden` on root, the header still scrolls away. This happens because:
1. ChatHistory has `flex-1 overflow-y-auto`
2. But without a containing wrapper with `min-h-0`, flex items don't shrink below their content size
3. The scroll bubbles up to the parent

## Solution

Wrap ChatHistory in a proper scroll container:

```tsx
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
  {/* FIXED HEADER */}
  <header className="flex-shrink-0">
    <CharacterStatus />
    <InventoryToggle />
    {showInventory && <InventoryPanel />}
  </header>

  {/* SCROLL CONTAINER - this is the key */}
  <div className="flex-1 min-h-0 overflow-hidden">
    <ChatHistory className="h-full overflow-y-auto" />
  </div>

  {/* FIXED: Combat/Death/Input */}
  ...
</div>
```

**Key insight**: The wrapper needs:
- `flex-1` - take remaining space
- `min-h-0` - allow shrinking below content size (CRITICAL)
- `overflow-hidden` - contain child scroll

And ChatHistory needs:
- `h-full` - fill the wrapper
- `overflow-y-auto` - scroll internally

## Alternative: Simpler Approach

If ChatHistory already handles its own scrolling, we just need the wrapper:

```tsx
{/* Scrollable middle section */}
<div className="flex-1 min-h-0 overflow-y-auto">
  <ChatHistory />
</div>
```

Here the wrapper does the scrolling, not ChatHistory.

## Files to Modify

```
frontend/src/pages/GamePage.tsx
frontend/src/components/game/ChatHistory.tsx  # May need to check its styles
```

## Acceptance Criteria

- [ ] Header visible on page load WITHOUT scrolling
- [ ] Scrolling chat does NOT move header
- [ ] Scrolling chat does NOT move action input
- [ ] Chat scrolls internally showing newest messages at bottom

## Debugging Step

Check ChatHistory component - does it have `overflow-y-auto`? If yes, we need the wrapper approach. If no, the wrapper should add it.

## Cost Impact

$0 - CSS only
