# PRP-16d: Layout Fix and Tool Keywords

**Created**: 2026-01-14
**Initial**: `initials/init-16d-layout-and-tools.md`
**Status**: Ready

---

## Overview

### Problem Statement

PRP-16c introduced a layout regression: changing `h-[calc(100vh-4rem)]` to `h-screen` fixed the status bar clipping, but now the entire page scrolls instead of just the chat area. When scrolling chat, the status bar and action input scroll out of view.

Additionally, common tools like "shovel" are not being added to inventory because they're not in the QUEST_KEYWORDS list.

### Proposed Solution

1. **Layout Fix**: Restructure GamePage to ensure only ChatHistory scrolls. The header (status bar + inventory toggle) and footer (action input) must be fixed/sticky.

2. **Tool Keywords**: Add common tool words to QUEST_KEYWORDS so items like "shovel", "pickaxe", "axe" can be dynamically created.

### Success Criteria
- [ ] Status bar **always visible** at top, never scrolls away
- [ ] Inventory toggle bar **always visible** below status bar
- [ ] Only chat history scrolls when content overflows
- [ ] Action input **always visible** at bottom
- [ ] Buying/finding tools (shovel, pickaxe, hammer, etc.) adds them to inventory

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview
- `prps/prp-16c-final-inventory-fixes.md` - Previous layout changes (h-screen)
- `initials/init-16c-final-inventory-fixes.md` - Context on layout issues

### Dependencies
- PRP-16c (Complete) - Previous inventory and UX fixes

### Files to Modify
```
frontend/src/pages/GamePage.tsx    # Fix flexbox layout structure
lambdas/shared/items.py            # Add tool keywords
```

---

## Technical Specification

### Layout Analysis

**Current Problem**:
The current structure has `overflow-hidden` on the main container but the middle section (`flex-1 min-h-0 overflow-hidden flex flex-col`) contains ChatHistory which also has `flex-1 overflow-y-auto`. The nested flex containers with `overflow-hidden` and `min-h-0` conflict.

**Solution**:
Remove the extra wrapper around ChatHistory and ensure the scrolling happens only in ChatHistory itself:

```tsx
<div className="h-screen flex flex-col bg-gray-900">
  {/* FIXED HEADER */}
  <header className="flex-shrink-0">
    <CharacterStatus />
    <InventoryToggle />
    {showInventory && <InventoryPanel />}
  </header>

  {/* SCROLLABLE CHAT - flex-1 min-h-0 allows shrinking, overflow-y-auto for scroll */}
  <ChatHistory className="flex-1 min-h-0" />  {/* ChatHistory already has overflow-y-auto */}

  {/* Combat/Death screens if needed */}

  {/* FIXED FOOTER */}
  <ActionInput className="flex-shrink-0" />
</div>
```

Key insight: ChatHistory already has `flex-1 overflow-y-auto`. The problem is the intermediate `<div className="flex-1 min-h-0 overflow-hidden flex flex-col">` wrapper which adds conflicting overflow behavior.

### Tool Keywords

Add these common tools to QUEST_KEYWORDS:
```python
# Tools
"shovel", "pickaxe", "axe", "hatchet", "hoe", "hammer", "saw",
"chisel", "tongs", "pliers", "wrench", "crowbar", "lever",
"rake", "broom", "mop", "brush", "sponge", "file", "rasp",
"anvil", "bellows", "trowel", "scythe", "sickle", "flint",
```

---

## Implementation Steps

### Step 1: Fix GamePage Layout Structure
**Files**: `frontend/src/pages/GamePage.tsx`

Restructure the layout to ensure proper fixed header/footer behavior:

1. Remove the intermediate wrapper div around ChatHistory
2. Keep `flex-shrink-0` on header sections
3. Apply `flex-1 min-h-0` directly to ChatHistory's parent context
4. Keep ActionInput at bottom with `flex-shrink-0`

**Before** (lines 113-173):
```tsx
return (
  <div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
    {/* Fixed header section - never scrolls */}
    <div className="flex-shrink-0 bg-gray-900 z-10">
      {/* ... header content ... */}
    </div>

    {/* Scrollable content area - takes remaining space */}
    <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
      {/* Chat history - scrollable middle */}
      <ChatHistory messages={messages} isLoading={isSendingAction} />
      {/* Combat/Death screens */}
    </div>

    {/* Action input */}
    {!characterDead && (
      <ActionInput ... />
    )}
  </div>
);
```

**After**:
```tsx
return (
  <div className="flex flex-col h-screen bg-gray-900">
    {/* Fixed header section - never scrolls */}
    <header className="flex-shrink-0 bg-gray-900 z-10">
      {/* ... header content ... */}
    </header>

    {/* Chat history - scrollable, takes remaining space */}
    <ChatHistory messages={messages} isLoading={isSendingAction} />

    {/* Combat UI - shown when turn-based combat is active */}
    {combat && combat.active && (
      <div className="flex-shrink-0">
        <CombatUI ... />
      </div>
    )}

    {/* Legacy combat status */}
    {combatActive && (!combat || !combat.active) && (
      <div className="flex-shrink-0">
        <CombatStatus ... />
      </div>
    )}

    {/* Death screen */}
    {characterDead && (
      <div className="flex-shrink-0">
        <DeathScreen ... />
      </div>
    )}

    {/* Action input - fixed at bottom */}
    {!characterDead && (
      <div className="flex-shrink-0">
        <ActionInput ... />
      </div>
    )}

    <TokenCounter usage={usage} />
  </div>
);
```

Key changes:
- Remove `overflow-hidden` from root (it conflicts with child scrolling)
- Remove the intermediate wrapper div around ChatHistory
- Use semantic `<header>` tag
- Wrap combat/death/input in `flex-shrink-0` divs to prevent them from being compressed

**Validation**:
- [ ] Status bar stays fixed when scrolling chat
- [ ] Action input stays fixed at bottom
- [ ] Only chat area scrolls

### Step 2: Add Tool Keywords
**Files**: `lambdas/shared/items.py`

Add common tool keywords to the QUEST_KEYWORDS list so items like "shovel" can be dynamically created.

Add these keywords after the "Common objects (narrative items)" section:

```python
QUEST_KEYWORDS = [
    # ... existing keywords ...
    # Common objects (narrative items)
    "rock",
    "stone",
    # ... existing ...
    "specimen",
    # Tools (commonly purchased/found)
    "shovel",
    "pickaxe",
    "axe",
    "hatchet",
    "hoe",
    "hammer",
    "saw",
    "chisel",
    "tongs",
    "pliers",
    "wrench",
    "crowbar",
    "lever",
    "rake",
    "broom",
    "mop",
    "brush",
    "sponge",
    "file",
    "rasp",
    "anvil",
    "bellows",
    "trowel",
    "scythe",
    "sickle",
    "flint",
    "needle",
    "scissors",
    "shears",
    "hook",
    "net",
    "trap",
    "snare",
    "cage",
    "chain",
    "padlock",
    "lock",
    "lantern",
    "lamp",
    "compass",
    "spyglass",
    "whistle",
    "bell",
    "gong",
    "drum",
]
```

**Validation**:
- [ ] Unit tests pass
- [ ] `find_item_by_name("shovel")` returns a valid ItemDefinition

### Step 3: Run Tests and Deploy
**Files**: N/A

```bash
# Backend tests
cd lambdas && .venv/bin/pytest

# Frontend tests (if any layout-related tests exist)
cd frontend && npm test

# Bump version
# Edit frontend/package.json: "version": "0.13.5"

# Build and deploy
cd frontend && npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"

# Deploy backend (for items.py changes)
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip
```

**Validation**:
- [ ] All tests pass
- [ ] Version bumped to 0.13.5
- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] CloudFront invalidated

---

## Testing Requirements

### Unit Tests
- Existing tests should pass (no new tests needed for CSS changes)
- `find_item_by_name("shovel")` should return ItemDefinition with item_type=QUEST

### Manual Testing
1. Load game page
2. Verify status bar is visible at top
3. Send multiple actions to generate chat content
4. Scroll chat down - status bar should stay fixed
5. Scroll chat down - action input should stay fixed at bottom
6. Buy a shovel in-game (`I want to buy a shovel`)
7. Check inventory - shovel should appear

---

## Integration Test Plan

### Prerequisites
- Backend deployed to prod
- Frontend deployed to S3
- CloudFront cache invalidated

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Load game page | Status bar visible with name, HP, XP, Gold | ☐ |
| 2 | Send 5+ actions to fill chat | Chat fills with messages | ☐ |
| 3 | Scroll chat down | Status bar stays fixed at top | ☐ |
| 4 | Scroll chat down | Action input stays fixed at bottom | ☐ |
| 5 | Scroll chat up | Can see earlier messages | ☐ |
| 6 | Open inventory toggle | Inventory panel appears below status | ☐ |
| 7 | Scroll chat with inventory open | Both status bar AND inventory stay visible | ☐ |
| 8 | Type "I want to buy a shovel" | DM response with +shovel in state | ☐ |
| 9 | Check inventory | Shovel appears in inventory list | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] No layout shifts when scrolling
- [ ] Touch scrolling works on mobile

---

## Error Handling

### Edge Cases
- **Empty chat**: Layout should still show header and footer with empty middle
- **Very long inventory**: Inventory panel has max-h-48 with overflow-y-auto (unchanged)
- **Combat UI visible**: Combat UI should appear below chat but above action input

---

## Cost Impact

### Claude API
- $0 - No AI changes

### AWS
- $0 - CSS and keyword list changes only

---

## Open Questions

None - requirements are clear from testing.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Requirements are very clear from testing |
| Feasibility | 9 | Standard flexbox layout pattern |
| Completeness | 9 | All issues addressed |
| Alignment | 10 | Pure bugfix, no cost impact |
| **Overall** | 9.5 | High confidence |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-16c)
- [x] Success criteria are measurable
