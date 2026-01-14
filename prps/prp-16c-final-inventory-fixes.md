# PRP-16c: Final Inventory & UX Fixes

**Created**: 2026-01-14
**Initial**: `initials/init-16c-final-inventory-fixes.md`
**Status**: Ready

---

## Overview

### Problem Statement

Four remaining issues discovered after PRP-16a and PRP-16b:

1. **Status bar clipping**: Character name/level/HP is cut off at the top of the viewport. The `h-[calc(100vh-4rem)]` assumes a 4rem nav bar but the game page doesn't have one visible.

2. **Item acquisition not working**: DM output `+small rock` but item wasn't added because "small rock" isn't in the catalog and doesn't match any `QUEST_KEYWORDS` (no "rock" or "stone" keyword exists).

3. **No auto-focus on text input**: Player has to click the input box after every action.

4. **Narrative wrapped in double quotes**: Some DM responses are wrapped in quotes like `"As you storm out..."`.

### Proposed Solution

1. **Fix layout**: Change from `h-[calc(100vh-4rem)]` to `h-screen` and remove nav bar assumption since the game page is full-screen.

2. **Expand QUEST_KEYWORDS**: Add common object keywords like "rock", "stone", "pebble", "shell", "leaf", etc. to allow flexible narrative items.

3. **Add auto-focus**: Add `useRef` and `useEffect` hooks to ActionInput to focus on mount and after each action.

4. **Clean double quotes**: Add quote stripping to `clean_narrator_output()`.

### Success Criteria

- [ ] Character status bar (name, level, HP, XP, Gold) fully visible - not clipped
- [ ] Scrolling chat doesn't affect status bar visibility
- [ ] Picking up non-catalog items like "small rock" adds them to inventory
- [ ] Text input auto-focused on page load
- [ ] Text input re-focuses after each action completes
- [ ] Narrative text not wrapped in double quotes

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Data models
- `prps/prp-16b-inventory-ui-polish.md` - Previous fix (COMPLETE)
- `prps/prp-16a-frontend-inventory-sync.md` - Inventory sync fix (COMPLETE)

### Dependencies

- Required: PRP-16b (inventory UI polish) - COMPLETE

### Files to Modify

```
frontend/src/pages/GamePage.tsx                  # Layout fix for status bar
frontend/src/components/game/ActionInput.tsx    # Auto-focus
lambdas/shared/items.py                         # Add QUEST_KEYWORDS
lambdas/dm/combat_narrator.py                   # Strip surrounding quotes
```

---

## Technical Specification

### Layout Fix

**Current** (GamePage.tsx line 114):
```tsx
<div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-900 overflow-hidden">
```

**Problem**: The `4rem` subtraction assumes a nav bar exists. On the game page, there's no nav bar visible, so we're cutting off 4rem from the top for nothing.

**New**:
```tsx
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
```

### QUEST_KEYWORDS Addition

**Current keywords** (items.py): key, letter, note, scroll, ring, amulet, token, locket, pendant, coin, gem, map, journal, book, vial, pouch, badge, seal, charm, relic, artifact, orb, crystal, skull, bone, feather, claw, fang, talisman, idol, medallion, brooch, crown, scepter, rod, wand

**Missing common objects**: rock, stone, pebble, shell, leaf, flower, herb, root, berry, mushroom, stick, twig, branch, cloth, rag, string, rope, bottle, jar, cup, bowl, plate, spoon, fork, knife (tool), hammer, nail, pin, button, thread, needle, candle, lantern, mirror, comb, brush, soap, towel, blanket, pillow, bag, sack, box, crate, barrel, bucket, pot, pan, tool

**Add these keywords**:
```python
QUEST_KEYWORDS = [
    # Existing quest items
    "key", "letter", "note", "scroll", "ring", "amulet", "token", "locket",
    "pendant", "coin", "gem", "map", "journal", "book", "vial", "pouch",
    "badge", "seal", "charm", "relic", "artifact", "orb", "crystal", "skull",
    "bone", "feather", "claw", "fang", "talisman", "idol", "medallion",
    "brooch", "crown", "scepter", "rod", "wand",
    # Common objects (narrative items)
    "rock", "stone", "pebble", "shell", "leaf", "flower", "herb", "root",
    "berry", "mushroom", "stick", "twig", "branch", "cloth", "rag", "string",
    "rope", "bottle", "jar", "cup", "bowl", "plate", "candle", "mirror",
    "bag", "sack", "box", "crate", "barrel", "bucket", "trinket", "bauble",
    "fragment", "shard", "piece", "part", "sample", "specimen",
]
```

### Auto-Focus Implementation

**ActionInput.tsx changes**:
```tsx
import { useState, useCallback, useRef, useEffect, KeyboardEvent } from 'react';

export function ActionInput({ onSend, disabled = false, isLoading = false, placeholder }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Re-focus after action completes (isLoading transitions from true to false)
  useEffect(() => {
    if (!isLoading) {
      textareaRef.current?.focus();
    }
  }, [isLoading]);

  // ... existing code ...

  return (
    <div className="border-t border-gray-700 bg-gray-800 p-4">
      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          autoFocus
          // ... rest unchanged
        />
```

### Quote Stripping

**combat_narrator.py changes** (add to `clean_narrator_output`):
```python
def clean_narrator_output(text: str) -> str:
    if not text:
        return ""

    # Strip surrounding double quotes if present (Mistral sometimes wraps responses)
    text = text.strip()
    if text.startswith('"') and text.endswith('"') and len(text) > 2:
        text = text[1:-1].strip()

    lines = text.split("\n")
    # ... rest unchanged
```

---

## Implementation Steps

### Step 1: Fix GamePage Layout

**Files**: `frontend/src/pages/GamePage.tsx`

Change the root container from `h-[calc(100vh-4rem)]` to `h-screen`:

```tsx
// Line 114: Change from
<div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-900 overflow-hidden">

// To
<div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
```

**Validation**:
- [ ] Frontend builds without errors
- [ ] Status bar fully visible
- [ ] No clipping at top

### Step 2: Add Auto-Focus to ActionInput

**Files**: `frontend/src/components/game/ActionInput.tsx`

1. Add `useRef` and `useEffect` to imports
2. Create ref for textarea
3. Add effect to focus on mount
4. Add effect to focus when loading completes
5. Add `ref` and `autoFocus` props to textarea

```tsx
import { useState, useCallback, useRef, useEffect, KeyboardEvent } from 'react';

// Inside component:
const textareaRef = useRef<HTMLTextAreaElement>(null);

// Auto-focus on mount
useEffect(() => {
  textareaRef.current?.focus();
}, []);

// Re-focus after action completes
useEffect(() => {
  if (!isLoading) {
    textareaRef.current?.focus();
  }
}, [isLoading]);

// Add to textarea:
<textarea
  ref={textareaRef}
  autoFocus
  // ... rest unchanged
/>
```

**Validation**:
- [ ] Frontend builds
- [ ] Input focused on page load
- [ ] Input re-focused after sending action

### Step 3: Expand QUEST_KEYWORDS

**Files**: `lambdas/shared/items.py`

Add common object keywords to enable dynamic item creation for narrative items:

```python
QUEST_KEYWORDS = [
    # Existing quest items
    "key", "letter", "note", "scroll", "ring", "amulet", "token", "locket",
    "pendant", "coin", "gem", "map", "journal", "book", "vial", "pouch",
    "badge", "seal", "charm", "relic", "artifact", "orb", "crystal", "skull",
    "bone", "feather", "claw", "fang", "talisman", "idol", "medallion",
    "brooch", "crown", "scepter", "rod", "wand",
    # Common objects (narrative items)
    "rock", "stone", "pebble", "shell", "leaf", "flower", "herb", "root",
    "berry", "mushroom", "stick", "twig", "branch", "cloth", "rag", "string",
    "rope", "bottle", "jar", "cup", "bowl", "plate", "candle", "mirror",
    "bag", "sack", "box", "crate", "barrel", "bucket", "trinket", "bauble",
    "fragment", "shard", "piece", "part", "sample", "specimen",
]
```

**Validation**:
- [ ] Backend tests pass
- [ ] `find_item_by_name("small rock")` returns an ItemDefinition

### Step 4: Strip Surrounding Quotes from Narrative

**Files**: `lambdas/dm/combat_narrator.py`

Add quote stripping at the start of `clean_narrator_output()`:

```python
def clean_narrator_output(text: str) -> str:
    """Clean AI output by removing any prompt leakage."""
    if not text:
        return ""

    # Strip surrounding double quotes if present (Mistral sometimes wraps responses)
    text = text.strip()
    if text.startswith('"') and text.endswith('"') and len(text) > 2:
        text = text[1:-1].strip()

    lines = text.split("\n")
    # ... rest of function unchanged
```

**Validation**:
- [ ] Backend tests pass
- [ ] Test that `clean_narrator_output('"Hello world"')` returns `"Hello world"`

### Step 5: Run Tests and Deploy

**Files**: All modified files

```bash
# Backend tests
cd lambdas && .venv/bin/pytest -q

# Frontend tests and build
cd frontend && npm test -- --run && npm run build

# Deploy backend
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip

# Bump version in package.json to 0.13.4
# Deploy frontend
npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] Backend tests pass
- [ ] Frontend builds
- [ ] Deployed to prod

---

## Testing Requirements

### Unit Tests

**Backend**:
- Test `clean_narrator_output('"quoted text"')` returns `"quoted text"`
- Test `clean_narrator_output('normal text')` returns `"normal text"`
- Test `find_item_by_name("small rock")` returns ItemDefinition with type QUEST

**Frontend**:
- No new unit tests required (UI behavior)

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
| 1 | Load game page with existing character | Status bar fully visible - name, level, HP bar, XP, Gold all showing, no clipping | ☐ |
| 2 | Check text input | Input field should be focused automatically (cursor blinking) | ☐ |
| 3 | Type and send an action | After response arrives, cursor should return to input | ☐ |
| 4 | Type "I pick up a small rock" | "Small Rock" should appear in inventory | ☐ |
| 5 | Check narrative text | No surrounding double quotes | ☐ |
| 6 | Scroll chat history | Status bar stays fully visible, not clipped | ☐ |

### Browser Checks

- [ ] No JavaScript errors in Console
- [ ] No layout shift when scrolling
- [ ] Status bar doesn't flicker or get cut off
- [ ] Input maintains focus after actions

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Unknown item (no keyword match) | DM tries to give item with no matching keyword | Log warning, skip silently |

### Edge Cases

- Empty inventory: Shows "Your pack is empty" message
- Very long item names: Truncated to 30 chars in item_id
- Quotes inside quotes: Only strip outer surrounding quotes
- Single quote character: `"` alone should not cause issues

---

## Cost Impact

### Claude API

- No change - same AI calls

### AWS

- No new resources
- Estimated impact: $0

---

## Open Questions

None - requirements are clearly defined from user testing.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Clear issues with specific fixes |
| Feasibility | 10 | Simple changes, no architectural impact |
| Completeness | 9 | All reported issues addressed |
| Alignment | 10 | UX polish, no budget impact |
| **Overall** | **9.75** | High confidence - straightforward fixes |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated ($0)
- [x] Dependencies are listed (PRP-16b)
- [x] Success criteria are measurable
