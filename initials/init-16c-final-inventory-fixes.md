# init-16c-final-inventory-fixes

## Overview

Final round of fixes for inventory system and UX polish. Previous fixes got quantity display and item removal working, but status bar clipping, item acquisition, and input focus still need work.

## Dependencies

- init-16b-inventory-ui-polish (COMPLETE)

## Confirmed Working

- ✅ Quantity display inline: `Rations (7)`, `Torch (3)`
- ✅ Single items show no quantity badge
- ✅ Item removal works and syncs to UI
- ✅ Inventory toggle visible when scrolling

## Problems

### 1. Status Bar Still Clipped at Top
The character name/level is still being cut off at the top of the viewport. Previous fix (removing `sticky top-0`) didn't resolve it. Need deeper investigation of the layout.

### 2. Item Acquisition Not Working
DM output `+small rock` but item wasn't added to inventory. 

**Root cause**: "small rock" is not in the item catalog, so `find_item_by_name()` returns `None` and the item is rejected.

The PRP-15 additions note mentioned adding dynamic quest item creation for items matching certain keywords, but this may not have been implemented. Need to either:
- Add the dynamic quest item fallback
- Or expand the catalog with common items

### 3. Text Input Needs Auto-Focus
Player has to click the text box after every action to continue typing. Should auto-focus after:
- Page load
- After sending an action (when response arrives)

### 4. Narrative Wrapped in Double Quotes
Some DM responses are wrapped in quotes like `"As you storm out..."`. This is a prompt issue - the DM is treating the response as dialogue.

## Proposed Solutions

### Fix 1: Status Bar Layout

The issue is likely the parent container height calculation. The `h-[calc(100vh-4rem)]` might be wrong if there's additional chrome (nav bar, etc).

Debug approach:
1. Check browser DevTools for actual computed heights
2. Ensure no negative margins or transforms
3. Try simpler layout without calc()

Possible fix - use `h-screen` with proper padding:
```tsx
<div className="h-screen pt-16 flex flex-col bg-gray-900">
  {/* pt-16 accounts for nav bar */}
  <div className="flex-shrink-0">
    <CharacterStatus />
    ...
  </div>
  ...
</div>
```

### Fix 2: Dynamic Quest Item Creation

In `find_item_by_name()`, add fallback for narrative items:

```python
def find_item_by_name(name: str) -> ItemDefinition | None:
    # ... existing exact match, partial match, aliases logic ...
    
    # Fallback: Create dynamic quest/misc item for unknown items
    # This allows DM to give narrative items like "small rock", "old letter"
    normalized = name.lower().strip()
    
    # Create a generic misc item for anything the DM wants to give
    # This preserves narrative flexibility while tracking items server-side
    return ItemDefinition(
        id=f"misc_{normalized.replace(' ', '_')[:30]}",
        name=name.title() if name.islower() else name,
        item_type=ItemType.MISC,
        value=0,
        description=f"A {normalized}."
    )
```

**Note**: This means ANY item the DM gives will be added. If we want to restrict to certain types, add keyword filtering:
```python
ALLOWED_MISC_KEYWORDS = ["rock", "stone", "letter", "note", "key", "ring", ...]
if not any(kw in normalized for kw in ALLOWED_MISC_KEYWORDS):
    logger.warning(f"Rejected non-catalog item: {name}")
    return None
```

### Fix 3: Auto-Focus Text Input

In `ActionInput.tsx` or wherever the input is:

```tsx
const inputRef = useRef<HTMLInputElement>(null);

// Auto-focus on mount
useEffect(() => {
  inputRef.current?.focus();
}, []);

// Re-focus after action completes (when isLoading changes from true to false)
useEffect(() => {
  if (!isLoading) {
    inputRef.current?.focus();
  }
}, [isLoading]);

return (
  <input
    ref={inputRef}
    autoFocus
    ...
  />
);
```

### Fix 4: Remove Double Quotes from Narrative

In the DM prompt (`output_format.py` or similar), add instruction:
```
Do NOT wrap your narrative in quotation marks. Write directly without surrounding quotes.
```

Or clean the response in the parser:
```python
def clean_narrative(text: str) -> str:
    # Remove surrounding quotes if present
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return text
```

## Acceptance Criteria

- [ ] Character status bar fully visible (name, level, HP, XP, Gold)
- [ ] No clipping at top of viewport
- [ ] Picking up items adds them to inventory (even non-catalog items like "small rock")
- [ ] Text input auto-focused on page load
- [ ] Text input re-focuses after each action
- [ ] Narrative not wrapped in double quotes

## Files to Modify

```
frontend/src/pages/GamePage.tsx                    # Layout fix for status bar
frontend/src/components/game/ActionInput.tsx      # Auto-focus
lambdas/shared/items.py                           # Dynamic item creation fallback
lambdas/dm/prompts/output_format.py               # No quotes instruction
lambdas/dm/parser.py                              # Quote cleaning (backup)
```

## Testing Plan

### Manual Tests
1. Load game → status bar fully visible
2. Type without clicking input → should work immediately
3. Send action → cursor returns to input automatically
4. Pick up non-catalog item ("small rock") → appears in inventory
5. Check narrative → no surrounding double quotes

## Cost Impact

$0 - No additional API calls

## Notes

The dynamic item creation is a balance between flexibility and game balance. For a roguelike, allowing ANY item might be too permissive. Consider restricting to misc/quest items only (no weapons/armor).
