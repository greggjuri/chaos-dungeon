# init-16g-chathistory-scroll-fix

## Overview

Fix the nested scroll issue in ChatHistory. DevTools confirmed the wrapper exists but scroll is still broken.

## Problem (from DevTools)

```
header.getBoundingClientRect().top = -133  // Header scrolled off by 133px
```

Structure found:
```html
<div class="flex-1 min-h-0 overflow-hidden">        <!-- Wrapper from 16f -->
  <div class="flex-1 overflow-y-auto px-4 py-4">   <!-- ChatHistory's own container -->
    ...messages...
  </div>
</div>
```

**Issue**: Two nested flex containers both trying to handle overflow. The outer wrapper has `overflow-hidden` but ChatHistory has `flex-1 overflow-y-auto`. The `flex-1` on ChatHistory makes it grow to content size, breaking containment.

## Solution

Change the wrapper to `overflow-y-auto` and give ChatHistory `h-full` instead of `flex-1`:

**In GamePage.tsx**, change wrapper from:
```tsx
<div className="flex-1 min-h-0 overflow-hidden">
```
to:
```tsx
<div className="flex-1 min-h-0 overflow-y-auto">
```

**In ChatHistory.tsx**, change the root container from:
```tsx
<div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
```
to:
```tsx
<div className="h-full px-4 py-4 space-y-4">
```

This makes:
- Wrapper: handles the scroll (`overflow-y-auto`)
- ChatHistory: fills wrapper exactly (`h-full`), no scroll of its own

## Files to Modify

```
frontend/src/pages/GamePage.tsx           # Change overflow-hidden to overflow-y-auto
frontend/src/components/game/ChatHistory.tsx  # Change flex-1 overflow-y-auto to h-full
```

## Acceptance Criteria

- [ ] Header visible on page load (no scrolling needed)
- [ ] header.getBoundingClientRect().top >= 0
- [ ] Scrolling chat does not move header
- [ ] Chat auto-scrolls to show newest messages

## Cost Impact

$0 - CSS only
