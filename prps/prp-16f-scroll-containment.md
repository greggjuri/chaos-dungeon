# PRP-16f: Scroll Containment Fix

**Created**: 2026-01-14
**Initial**: `initials/init-16f-scroll-containment.md`
**Status**: Ready

---

## Overview

### Problem Statement

Despite `overflow-hidden` on the root container, the header still scrolls away with the chat. This is because ChatHistory has `flex-1 overflow-y-auto` but lacks `min-h-0`, so it doesn't shrink below its content size in a flex column layout. The scroll "bubbles up" to the parent.

### Proposed Solution

Wrap ChatHistory in a scroll containment wrapper that has:
- `flex-1` - take remaining space
- `min-h-0` - **critical**: allows flex item to shrink below content size
- `overflow-hidden` - contain child scrolling

This is the "missing piece" that breaks flexbox scroll containment.

### Success Criteria
- [ ] Header visible on page load **without scrolling**
- [ ] Scrolling chat does **not** move header
- [ ] Scrolling chat does **not** move action input
- [ ] Chat auto-scrolls to newest messages at bottom
- [ ] Resizable inventory panel still works

---

## Context

### Related Documentation
- `prps/prp-16e-layout-hotfix.md` - Added back overflow-hidden (still not working)
- `prps/prp-16d-layout-and-tools.md` - Removed wrapper (caused regression)

### Dependencies
- PRP-16e (Complete) - Has overflow-hidden and resizable inventory

### Files to Modify
```
frontend/src/pages/GamePage.tsx    # Add scroll containment wrapper
```

---

## Technical Specification

### Root Cause Analysis

**Current structure**:
```tsx
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
  <header className="flex-shrink-0">...</header>

  <ChatHistory />  {/* Has flex-1 overflow-y-auto, but missing min-h-0 */}

  <div className="flex-shrink-0">...</div>  {/* Combat/Input */}
</div>
```

**The problem**: In a flex column layout, a child with `flex-1` will try to be at least as tall as its content. Even with `overflow-y-auto`, if the content is taller than the available space, the flex item grows to accommodate it, causing the parent to scroll.

**The fix**: `min-h-0` tells flexbox "this item can shrink to 0 height if needed", allowing the overflow to be properly contained.

**Fixed structure**:
```tsx
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
  <header className="flex-shrink-0">...</header>

  {/* Scroll containment wrapper - THE KEY FIX */}
  <div className="flex-1 min-h-0 overflow-hidden">
    <ChatHistory />  {/* Now properly contained */}
  </div>

  <div className="flex-shrink-0">...</div>  {/* Combat/Input */}
</div>
```

### Why This Works

1. `flex-1` on wrapper: Takes all remaining vertical space
2. `min-h-0` on wrapper: Allows shrinking below content height (CRITICAL)
3. `overflow-hidden` on wrapper: Contains the scroll to ChatHistory
4. ChatHistory's `flex-1 overflow-y-auto`: Scrolls within the container

---

## Implementation Steps

### Step 1: Add Scroll Containment Wrapper
**Files**: `frontend/src/pages/GamePage.tsx`

Wrap the ChatHistory component in a scroll containment div.

**Current code** (line 180-181):
```tsx
      {/* Chat history - scrollable, takes remaining space */}
      <ChatHistory messages={messages} isLoading={isSendingAction} />
```

**Change to**:
```tsx
      {/* Scroll containment wrapper - flex-1 min-h-0 is critical for proper containment */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <ChatHistory messages={messages} isLoading={isSendingAction} />
      </div>
```

**Validation**:
- [ ] Header stays fixed when scrolling chat
- [ ] Action input stays fixed at bottom
- [ ] Chat scrolls internally

### Step 2: Run Tests and Deploy
**Files**: N/A

```bash
# Frontend tests
cd frontend && npm test -- --run

# Bump version
# Edit frontend/package.json: "version": "0.13.7"

# Build and deploy
cd frontend && npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] All tests pass
- [ ] Version bumped to 0.13.7
- [ ] Frontend deployed
- [ ] CloudFront invalidated

---

## Testing Requirements

### Unit Tests
- Existing tests should pass (no logic changes)

### Manual Testing
1. Load game → header visible at top immediately (no scroll needed)
2. Send multiple actions to fill chat
3. Scroll chat → header stays fixed
4. Scroll chat → action input stays fixed
5. Open inventory → inventory still works
6. Drag resize handle → inventory resizes correctly

---

## Integration Test Plan

### Prerequisites
- Frontend deployed to S3
- CloudFront cache invalidated

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Load game page fresh | Header visible at TOP without scrolling | ☐ |
| 2 | Note scroll position | Page NOT scrolled down on load | ☐ |
| 3 | Send 5+ actions | Chat fills with content | ☐ |
| 4 | Scroll chat down | Header stays fixed at top | ☐ |
| 5 | Scroll chat down | Action input stays fixed at bottom | ☐ |
| 6 | Check newest message | Visible at bottom of chat area | ☐ |
| 7 | Open inventory | Panel appears, header still fixed | ☐ |
| 8 | Resize inventory | Drag handle works correctly | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] No layout shift on page load

---

## Error Handling

### Edge Cases
- **Empty chat**: Layout still correct with empty middle area
- **Single message**: No scroll needed, layout correct
- **Window resize**: Containment adapts to new viewport size

---

## Cost Impact

### Claude API
- $0 - No AI changes

### AWS
- $0 - CSS wrapper only

---

## Open Questions

None - root cause is well understood (missing `min-h-0`).

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Root cause identified: missing min-h-0 |
| Feasibility | 10 | Single wrapper div addition |
| Completeness | 10 | One-line fix for the core issue |
| Alignment | 10 | Pure CSS fix, $0 cost |
| **Overall** | 10 | Very high confidence |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling covers edge cases
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-16e)
- [x] Success criteria are measurable
