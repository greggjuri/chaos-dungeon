# PRP-16g: ChatHistory Scroll Fix

**Created**: 2026-01-14
**Initial**: `initials/init-16g-chathistory-scroll-fix.md`
**Status**: Ready

---

## Overview

### Problem Statement

DevTools confirmed the header is scrolling off-screen by 133px:
```
header.getBoundingClientRect().top = -133
```

The issue is nested scroll containers that conflict:
1. **Wrapper**: `flex-1 min-h-0 overflow-hidden`
2. **ChatHistory**: `flex-1 overflow-y-auto`

ChatHistory's `flex-1` makes it grow to content size, then attempts to scroll within itself. But since it's inside an `overflow-hidden` container, the scroll behavior breaks.

### Proposed Solution

Move the scroll responsibility to the **wrapper** and make ChatHistory simply **fill** it:

1. **Wrapper**: Change `overflow-hidden` to `overflow-y-auto` (handles scrolling)
2. **ChatHistory**: Change `flex-1 overflow-y-auto` to `h-full` (fills container, no scroll)

### Success Criteria
- [ ] Header visible on page load (no scrolling needed)
- [ ] `header.getBoundingClientRect().top >= 0` in DevTools
- [ ] Scrolling chat does **not** move header
- [ ] Chat auto-scrolls to show newest messages

---

## Context

### Related Documentation
- `prps/prp-16f-scroll-containment.md` - Added wrapper (still not working)
- DevTools inspection showing header at -133px

### Dependencies
- PRP-16f (Complete) - Has the scroll containment wrapper

### Files to Modify
```
frontend/src/pages/GamePage.tsx           # Change overflow-hidden to overflow-y-auto
frontend/src/components/game/ChatHistory.tsx  # Change flex-1 overflow-y-auto to h-full
```

---

## Technical Specification

### Current Structure (Broken)

```html
<div class="flex-1 min-h-0 overflow-hidden">        <!-- Wrapper: blocks overflow -->
  <div class="flex-1 overflow-y-auto px-4 py-4">   <!-- ChatHistory: tries to scroll -->
    ...messages...
  </div>
</div>
```

**Problem**: Two flex items competing. ChatHistory's `flex-1` grows to content size inside the wrapper. The wrapper has `overflow-hidden`, which clips but doesn't properly contain the child's scroll.

### Fixed Structure

```html
<div class="flex-1 min-h-0 overflow-y-auto">       <!-- Wrapper: handles scroll -->
  <div class="h-full px-4 py-4">                   <!-- ChatHistory: fills wrapper -->
    ...messages...
  </div>
</div>
```

**Solution**:
- Wrapper handles ALL scrolling (`overflow-y-auto`)
- ChatHistory fills wrapper exactly (`h-full`), no scroll of its own

---

## Implementation Steps

### Step 1: Update Wrapper in GamePage
**Files**: `frontend/src/pages/GamePage.tsx`

Change the scroll containment wrapper from `overflow-hidden` to `overflow-y-auto`.

**Current code** (line 181):
```tsx
<div className="flex-1 min-h-0 overflow-hidden">
```

**Change to**:
```tsx
<div className="flex-1 min-h-0 overflow-y-auto">
```

**Validation**:
- [ ] Code compiles

### Step 2: Update ChatHistory Container
**Files**: `frontend/src/components/game/ChatHistory.tsx`

Change the root container from `flex-1 overflow-y-auto` to `h-full`.

**Current code** (line 31):
```tsx
className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
```

**Change to**:
```tsx
className="h-full px-4 py-4 space-y-4"
```

**Validation**:
- [ ] Code compiles
- [ ] Auto-scroll still works (uses scrollIntoView on bottomRef)

### Step 3: Run Tests and Deploy
**Files**: N/A

```bash
# Frontend tests
cd frontend && npm test -- --run

# Bump version
# Edit frontend/package.json: "version": "0.13.8"

# Build and deploy
cd frontend && npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] All tests pass
- [ ] Version bumped to 0.13.8
- [ ] Frontend deployed
- [ ] CloudFront invalidated

---

## Testing Requirements

### Unit Tests
- Existing tests should pass (no logic changes)

### Manual Testing
1. Load game → header visible at top immediately
2. Open DevTools → `document.querySelector('header').getBoundingClientRect().top` should be >= 0
3. Send multiple actions to fill chat
4. Scroll chat → header stays fixed
5. New message arrives → auto-scrolls to bottom

---

## Integration Test Plan

### Prerequisites
- Frontend deployed to S3
- CloudFront cache invalidated

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Load game page | Header visible at top (top >= 0) | ☐ |
| 2 | Run in DevTools: `document.querySelector('header').getBoundingClientRect().top` | Returns >= 0 | ☐ |
| 3 | Send 5+ actions | Chat fills with content | ☐ |
| 4 | Scroll chat down | Header stays fixed at top | ☐ |
| 5 | Scroll chat up | Can see earlier messages | ☐ |
| 6 | Send new action | Chat auto-scrolls to show response | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] Header stays at top on page load

---

## Error Handling

### Edge Cases
- **Empty chat**: Layout still correct, empty state message visible
- **Single message**: No scroll needed, layout correct
- **Auto-scroll**: `scrollIntoView` on bottomRef still works (wrapper handles scroll)

---

## Cost Impact

### Claude API
- $0 - No AI changes

### AWS
- $0 - CSS changes only

---

## Open Questions

None - root cause clearly identified via DevTools.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | DevTools confirmed exact issue |
| Feasibility | 10 | Two class changes |
| Completeness | 10 | Single responsibility for scroll |
| Alignment | 10 | Pure CSS fix, $0 cost |
| **Overall** | 10 | Very high confidence |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling covers edge cases
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-16f)
- [x] Success criteria are measurable
