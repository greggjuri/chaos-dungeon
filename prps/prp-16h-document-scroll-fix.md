# PRP-16h: Document Scroll Fix

**Created**: 2026-01-14
**Initial**: `initials/init-16h-document-scroll-fix.md`
**Status**: Ready

---

## Overview

### Problem Statement

DevTools confirmed that despite all previous fixes (16d-16g), the `<html>` element itself is scrolling:

```
HTML scrollTop: 182        // Document is scrolling!
Body height: 1286          // Body is taller than viewport
Window height: 1023        // Viewport height
```

The game container has `h-screen overflow-hidden` but the `<html>` element is scrollable because the body is taller than the viewport (1286 > 1023). The browser's default behavior allows the document to scroll even when our container restricts overflow.

### Proposed Solution

Prevent document-level scrolling by disabling overflow on `<html>` and `<body>` specifically when on the game page using a `useEffect` hook. This is scoped to only the game page so other pages (character selection, etc.) can scroll normally.

### Success Criteria
- [ ] `document.documentElement.scrollTop` returns 0
- [ ] Header visible on page load without scrolling
- [ ] Chat scrolls inside wrapper, not document
- [ ] Other pages (character select, home) still scroll normally
- [ ] Cleanup restores scroll on unmount (navigating away)

---

## Context

### Related Documentation
- `prps/prp-16g-chathistory-scroll-fix.md` - Fixed nested scroll containers
- `prps/prp-16f-scroll-containment.md` - Added flex-1 min-h-0 wrapper
- `prps/prp-16e-layout-hotfix.md` - Added resizable inventory
- DevTools inspection confirming HTML scrollTop: 182

### Dependencies
- PRP-16g (Complete) - Scroll containment wrapper in place

### Files to Modify
```
frontend/src/pages/GamePage.tsx    # Add useEffect to disable document scroll
```

---

## Technical Specification

### Root Cause Analysis

The layout hierarchy is correct:
```tsx
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
  <header className="flex-shrink-0">...</header>
  <div className="flex-1 min-h-0 overflow-y-auto">
    <ChatHistory /> {/* h-full fills container */}
  </div>
  <footer className="flex-shrink-0">...</footer>
</div>
```

However, the browser itself can scroll the `<html>` or `<body>` element independently of our game container. When the body's computed height exceeds viewport height, the browser enables document-level scrolling by default.

### Solution

Add a `useEffect` that:
1. Saves original overflow values (for restoration)
2. Sets `overflow: hidden` on both `<html>` and `<body>`
3. Cleans up on component unmount (restores original values)

```tsx
// Prevent document-level scrolling on game page
useEffect(() => {
  const html = document.documentElement;
  const body = document.body;

  // Save original values
  const originalHtmlOverflow = html.style.overflow;
  const originalBodyOverflow = body.style.overflow;

  // Disable scrolling
  html.style.overflow = 'hidden';
  body.style.overflow = 'hidden';

  return () => {
    // Restore on unmount
    html.style.overflow = originalHtmlOverflow;
    body.style.overflow = originalBodyOverflow;
  };
}, []);
```

### Why Not Global CSS?

A global CSS solution would affect ALL pages:
```css
html, body {
  overflow: hidden;
  height: 100%;
}
```

This would break scrolling on:
- Home page
- Character selection page
- Any future pages that need scrolling

The `useEffect` approach is better because it's scoped only to GamePage.

---

## Implementation Steps

### Step 1: Add Document Scroll Prevention
**Files**: `frontend/src/pages/GamePage.tsx`

Add `useEffect` import and the scroll prevention effect near the top of the component.

**Current imports** (line 4):
```tsx
import { useState, useCallback } from 'react';
```

**Change to**:
```tsx
import { useState, useCallback, useEffect } from 'react';
```

**Add after line 27** (after `inventoryHeight` state):
```tsx
// Prevent document-level scrolling on game page
useEffect(() => {
  const html = document.documentElement;
  const body = document.body;

  // Save original values
  const originalHtmlOverflow = html.style.overflow;
  const originalBodyOverflow = body.style.overflow;

  // Disable scrolling
  html.style.overflow = 'hidden';
  body.style.overflow = 'hidden';

  return () => {
    // Restore on unmount
    html.style.overflow = originalHtmlOverflow;
    body.style.overflow = originalBodyOverflow;
  };
}, []);
```

**Validation**:
- [ ] Code compiles
- [ ] `useEffect` added to imports

### Step 2: Run Tests and Deploy
**Files**: N/A

```bash
# Frontend tests
cd frontend && npm test -- --run

# Bump version
# Edit frontend/package.json: "version": "0.13.9"

# Build and deploy
cd frontend && npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] All tests pass
- [ ] Version bumped to 0.13.9
- [ ] Frontend deployed
- [ ] CloudFront invalidated

---

## Testing Requirements

### Unit Tests
- Existing tests should pass (no logic changes to game mechanics)

### Manual Testing
1. Load game → header visible at top immediately
2. Open DevTools Console → Run `document.documentElement.scrollTop` → Should return 0
3. Scroll chat → Header stays fixed at top
4. Navigate to character selection → That page should scroll normally
5. Navigate back to game → Scroll prevention re-enabled

---

## Integration Test Plan

### Prerequisites
- Frontend deployed to S3
- CloudFront cache invalidated

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Load game page fresh | Header visible at TOP without scrolling | ☐ |
| 2 | Run in DevTools: `document.documentElement.scrollTop` | Returns 0 | ☐ |
| 3 | Run in DevTools: `document.body.scrollTop` | Returns 0 | ☐ |
| 4 | Scroll chat content down | Header stays fixed at top | ☐ |
| 5 | Navigate to /characters | Page scrolls normally if content overflows | ☐ |
| 6 | Navigate back to game | Scroll prevention active again | ☐ |
| 7 | Send action → new message | Chat auto-scrolls, header stays fixed | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] Header stays at top on page load
- [ ] `getComputedStyle(document.documentElement).overflow` returns "hidden" on game page

---

## Error Handling

### Edge Cases
- **Component unmount during navigation**: Cleanup function restores overflow
- **Fast navigation**: React handles cleanup order automatically
- **SSR (if ever added)**: `document` access is guarded by being in `useEffect`

---

## Cost Impact

### Claude API
- $0 - No AI changes

### AWS
- $0 - JS/CSS changes only

---

## Open Questions

None - root cause clearly identified via DevTools.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | DevTools confirmed exact issue (HTML scrollTop: 182) |
| Feasibility | 10 | Simple useEffect hook |
| Completeness | 10 | Properly scoped, clean restoration |
| Alignment | 10 | Pure JS fix, $0 cost |
| **Overall** | 10 | Very high confidence |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling covers edge cases
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-16g)
- [x] Success criteria are measurable
