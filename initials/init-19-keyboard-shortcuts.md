# init-19-keyboard-shortcuts.md

## Overview

Add keyboard navigation to the game UI with panel overlays for inventory and character sheet. Remove the dedicated inventory button - replace with small icon buttons and keyboard shortcuts.

## Features

### 1. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `i` | Toggle inventory panel |
| `c` | Toggle character sheet panel |
| `Escape` | Close any open panel |

**Behavior:**
- Shortcuts only active when chat input is not focused
- Opening a panel closes any other open panel (mutually exclusive)
- Pressing same key again closes the panel (toggle)

### 2. Panel Overlay

**Design:**
- Semi-transparent overlay in center of screen
- Dark background with slight transparency (e.g., `bg-gray-900/95`)
- Consistent size for both panels (e.g., max-w-md or similar)
- Click outside panel to close
- Smooth fade-in/fade-out animation

**Inventory Panel:**
- Title: "Inventory" with backpack icon
- List of items with quantities (existing inventory display logic)
- Close button (X) in corner

**Character Sheet Panel:**
- Title: "Character" with person icon
- Character name
- Class and level (e.g., "Level 3 Fighter")
- HP: current / max
- XP: current value
- Gold: current value
- Ability scores in grid:
  - STR, INT, WIS
  - DEX, CON, CHA

### 3. Status Bar Icons

**Replace inventory button with two small icons:**
- Backpack icon → opens inventory
- Person icon → opens character sheet

**Icon styling:**
- Small size (20-24px)
- Muted color by default (gray-500)
- Brighten on hover (gray-300)
- Grouped together in status bar

### 4. Keyboard Hint

**Footer hint text:**
- Small muted text at bottom of game area
- Content: `I Inventory · C Character · Esc Close`
- Only visible when no panel is open
- Very subtle (text-xs, text-gray-600 or similar)
- Hidden when chat input is focused

## UI Changes Summary

**Remove:**
- Inventory button from status bar (the larger button)

**Add:**
- Small backpack icon in status bar
- Small person icon in status bar
- Character sheet panel component
- Keyboard shortcut handler
- Footer hint text

**Modify:**
- Inventory panel → centered overlay instead of side panel
- Panel state management (one panel at a time)

## Files to Modify

- `frontend/src/components/GameInterface.tsx` - Keyboard handler, panel state
- `frontend/src/components/StatusBar.tsx` - Replace button with icons
- `frontend/src/components/InventoryPanel.tsx` - Convert to overlay style
- `frontend/src/components/CharacterSheet.tsx` - New component

## Component Structure

```
GameInterface
├── StatusBar (with small icons)
├── ChatHistory
├── ChatInput
├── KeyboardHint (footer)
└── PanelOverlay (conditional)
    ├── InventoryPanel OR
    └── CharacterSheet
```

## Acceptance Criteria

1. Press `i` to open/close inventory overlay
2. Press `c` to open/close character sheet overlay
3. Press `Escape` to close any open panel
4. Opening one panel closes the other
5. Click outside panel closes it
6. Small backpack/person icons in status bar work on click
7. Keyboard shortcuts disabled when typing in chat input
8. Hint text visible at bottom when no panel open
9. Character sheet displays: name, class, level, HP, XP, gold, all 6 ability scores

## Testing

**Keyboard:**
1. Focus not on input → press `i` → inventory opens
2. Press `c` → inventory closes, character sheet opens
3. Press `Escape` → character sheet closes
4. Focus on chat input → press `i` → types "i" (shortcut disabled)

**Icons:**
1. Click backpack icon → inventory opens
2. Click person icon → character sheet opens
3. Click outside panel → closes

**Mobile (manual):**
1. Tap backpack icon → inventory opens
2. Tap person icon → character sheet opens
3. Tap outside → closes

## Dependencies

- Lucide React icons: `Package` (backpack), `User` (person)
- Character data already available in game state (name, class, level, hp, xp, gold, stats)

## Notes

- Keep dark fantasy aesthetic - muted colors, no bright UI elements
- Panels should feel like parchment/tome in a dark world
- Existing inventory logic (item list, quantities) is preserved, just re-styled
