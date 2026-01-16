# PRP-19: Keyboard Shortcuts and Panel Overlays

**Created**: 2026-01-16
**Initial**: `initials/init-19-keyboard-shortcuts.md`
**Status**: Ready

---

## Overview

### Problem Statement
The current inventory UI uses a collapsible panel in the header area which takes up vertical space. There's no character sheet view at all - players can only see basic stats (HP, XP, Gold) in the status bar, not their ability scores. Navigation relies entirely on mouse clicks.

### Proposed Solution
Replace the collapsible inventory with centered overlay panels accessible via keyboard shortcuts and small icons. Add a new character sheet panel showing full character details including ability scores.

**Key Changes:**
1. Add keyboard shortcuts: `i` (inventory), `c` (character), `Escape` (close)
2. Convert inventory from collapsible header panel to centered modal overlay
3. Create new CharacterSheet component with full character details
4. Replace inventory toggle button with small icon buttons in status bar
5. Add keyboard hint text in footer

### Success Criteria
- [ ] Press `i` opens/closes inventory overlay when not typing
- [ ] Press `c` opens/closes character sheet overlay when not typing
- [ ] Press `Escape` closes any open panel
- [ ] Opening one panel closes the other (mutually exclusive)
- [ ] Click outside panel closes it
- [ ] Small backpack icon in status bar opens inventory
- [ ] Small person icon in status bar opens character sheet
- [ ] Keyboard shortcuts disabled when chat input is focused
- [ ] Hint text visible at bottom: `I Inventory · C Character · Esc Close`
- [ ] Character sheet displays: name, class, level, HP, XP, gold, all 6 ability scores
- [ ] Smooth fade animation on panel open/close

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Frontend architecture (React + TypeScript + Tailwind)
- `docs/DECISIONS.md` - ADR-008 (React + Vite Frontend)

### Dependencies
- **Required**: None - frontend-only change
- **New dependency**: `lucide-react` for icons (Package, User icons)

### Files to Modify/Create
```
frontend/package.json                     # Add lucide-react dependency
frontend/src/pages/GamePage.tsx           # Panel state, keyboard handler, layout changes
frontend/src/components/game/CharacterStatus.tsx  # Add icon buttons
frontend/src/components/game/InventoryPanel.tsx   # Restyle as overlay panel
frontend/src/components/game/CharacterSheet.tsx   # NEW - full character details panel
frontend/src/components/game/PanelOverlay.tsx     # NEW - reusable overlay wrapper
frontend/src/components/game/KeyboardHint.tsx     # NEW - footer hint text
frontend/src/components/game/index.ts     # Export new components
```

---

## Technical Specification

### Component Structure
```
GamePage
├── CharacterStatus (with small icons)
├── ChatHistory (scroll container)
├── CombatUI / CombatStatus (conditional)
├── ActionInput
├── KeyboardHint (footer, hidden when panel open)
├── TokenCounter
└── PanelOverlay (conditional)
    ├── InventoryPanel OR
    └── CharacterSheet
```

### State Management
```typescript
// In GamePage.tsx
type PanelType = 'inventory' | 'character' | null;
const [activePanel, setActivePanel] = useState<PanelType>(null);

// Toggle panel (close if already open, else open and close other)
const togglePanel = (panel: PanelType) => {
  setActivePanel(prev => prev === panel ? null : panel);
};

// Close any panel
const closePanel = () => setActivePanel(null);
```

### Keyboard Handling
```typescript
// In GamePage.tsx - useEffect for keyboard shortcuts
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Skip if typing in input/textarea
    if (e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement) {
      return;
    }

    // Skip if modifier keys held
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    switch (e.key.toLowerCase()) {
      case 'i':
        e.preventDefault();
        togglePanel('inventory');
        break;
      case 'c':
        e.preventDefault();
        togglePanel('character');
        break;
      case 'escape':
        e.preventDefault();
        closePanel();
        break;
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

### New Components

#### PanelOverlay.tsx
```typescript
interface PanelOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}
```

#### CharacterSheet.tsx
```typescript
interface CharacterSheetProps {
  character: Character;
  snapshot: CharacterSnapshot | null;
}
```
Displays:
- Name, class, level
- HP (current/max with bar)
- XP, Gold
- Ability scores grid (STR, INT, WIS / DEX, CON, CHA)

#### KeyboardHint.tsx
```typescript
interface KeyboardHintProps {
  visible: boolean;  // Hidden when panel open or chat focused
}
```
Displays: `I Inventory · C Character · Esc Close`

---

## Implementation Steps

### Step 1: Add lucide-react Dependency
**Files**: `frontend/package.json`

Install lucide-react for icon support:
```bash
cd frontend && npm install lucide-react
```

**Validation**:
- [ ] Package installs without errors
- [ ] Import works: `import { Package, User, X } from 'lucide-react'`

### Step 2: Create PanelOverlay Component
**Files**: `frontend/src/components/game/PanelOverlay.tsx`

Create reusable overlay wrapper with:
- Semi-transparent dark backdrop
- Centered panel container (max-w-md)
- Title bar with icon and close button
- Click outside to close
- Fade animation (opacity transition)

```typescript
import { X } from 'lucide-react';

interface PanelOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}

export function PanelOverlay({ isOpen, onClose, title, icon, children }: PanelOverlayProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="bg-gray-900/95 border border-gray-700 rounded-lg w-full max-w-md mx-4 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2 text-amber-400 font-bold">
            {icon}
            <span>{title}</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
```

**Validation**:
- [ ] Component renders when isOpen=true
- [ ] Clicking backdrop calls onClose
- [ ] Clicking panel content does not close

### Step 3: Create CharacterSheet Component
**Files**: `frontend/src/components/game/CharacterSheet.tsx`

Create character details panel showing:
- Name, Class, Level (header area)
- HP bar (similar to CharacterStatus)
- XP and Gold
- Ability scores in 2x3 grid

```typescript
import { Character, CharacterSnapshot } from '../../types';

interface CharacterSheetProps {
  character: Character;
  snapshot: CharacterSnapshot | null;
}

export function CharacterSheet({ character, snapshot }: CharacterSheetProps) {
  const hp = snapshot?.hp ?? character.hp;
  const maxHp = snapshot?.max_hp ?? character.max_hp;
  const xp = snapshot?.xp ?? character.xp;
  const gold = snapshot?.gold ?? character.gold;
  const level = snapshot?.level ?? character.level;
  const abilities = character.abilities;

  // ... render full character details
}
```

**Validation**:
- [ ] All character data displays correctly
- [ ] Uses snapshot values when available
- [ ] Ability scores display in grid

### Step 4: Create KeyboardHint Component
**Files**: `frontend/src/components/game/KeyboardHint.tsx`

Small hint text at bottom of screen:

```typescript
interface KeyboardHintProps {
  visible: boolean;
}

export function KeyboardHint({ visible }: KeyboardHintProps) {
  if (!visible) return null;

  return (
    <div className="fixed bottom-2 left-1/2 -translate-x-1/2 z-30 text-gray-600 text-xs">
      I Inventory · C Character · Esc Close
    </div>
  );
}
```

**Validation**:
- [ ] Renders when visible=true
- [ ] Hidden when visible=false
- [ ] Properly positioned at bottom center

### Step 5: Update Component Exports
**Files**: `frontend/src/components/game/index.ts`

Add exports for new components:
```typescript
export { PanelOverlay } from './PanelOverlay';
export { CharacterSheet } from './CharacterSheet';
export { KeyboardHint } from './KeyboardHint';
```

**Validation**:
- [ ] All components export correctly
- [ ] No circular dependency issues

### Step 6: Add Icon Buttons to CharacterStatus
**Files**: `frontend/src/components/game/CharacterStatus.tsx`

Add small icon buttons for inventory and character sheet:

```typescript
import { Package, User } from 'lucide-react';

interface Props {
  character: Character;
  snapshot: CharacterSnapshot | null;
  onInventoryClick?: () => void;
  onCharacterClick?: () => void;
}
```

Add icon buttons after stats section:
```tsx
<div className="flex items-center gap-2">
  <button
    onClick={onInventoryClick}
    className="text-gray-500 hover:text-gray-300 transition-colors"
    title="Inventory (I)"
  >
    <Package size={20} />
  </button>
  <button
    onClick={onCharacterClick}
    className="text-gray-500 hover:text-gray-300 transition-colors"
    title="Character (C)"
  >
    <User size={20} />
  </button>
</div>
```

**Validation**:
- [ ] Icons display correctly
- [ ] Hover state works
- [ ] Click handlers fire

### Step 7: Update InventoryPanel for Overlay Style
**Files**: `frontend/src/components/game/InventoryPanel.tsx`

Minor styling adjustments for overlay context:
- Remove any padding that conflicts with overlay
- Ensure content fits within overlay container
- No structural changes needed - component already renders item list

**Validation**:
- [ ] Inventory displays correctly in overlay
- [ ] Scrolling works for long lists
- [ ] Use buttons still work in combat

### Step 8: Update GamePage with Panel System
**Files**: `frontend/src/pages/GamePage.tsx`

Major changes:
1. Remove `showInventory` and `inventoryHeight` state
2. Remove inventory toggle bar from header
3. Remove collapsible inventory panel
4. Add `activePanel` state
5. Add keyboard handler useEffect
6. Add PanelOverlay with conditional content
7. Add KeyboardHint component
8. Pass icon click handlers to CharacterStatus

```typescript
import { Package, User } from 'lucide-react';
import {
  // ... existing imports
  CharacterSheet,
  PanelOverlay,
  KeyboardHint,
} from '../components/game';

type PanelType = 'inventory' | 'character' | null;

export function GamePage() {
  const [activePanel, setActivePanel] = useState<PanelType>(null);

  // Keyboard handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      switch (e.key.toLowerCase()) {
        case 'i':
          e.preventDefault();
          setActivePanel(prev => prev === 'inventory' ? null : 'inventory');
          break;
        case 'c':
          e.preventDefault();
          setActivePanel(prev => prev === 'character' ? null : 'character');
          break;
        case 'escape':
          e.preventDefault();
          setActivePanel(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // ... rest of component
}
```

**Validation**:
- [ ] Keyboard shortcuts work
- [ ] Panels open/close correctly
- [ ] Opening one closes the other
- [ ] Escape closes any panel
- [ ] Chat input typing doesn't trigger shortcuts

### Step 9: Run Tests and Fix Any Issues
**Files**: All frontend test files

```bash
cd frontend && npm test
```

Update any tests affected by component changes.

**Validation**:
- [ ] All tests pass
- [ ] Lint passes: `npm run lint`

### Step 10: Manual Testing
**Files**: N/A (runtime testing)

Test all scenarios listed in acceptance criteria.

**Validation**:
- [ ] All keyboard shortcuts work
- [ ] Icons in status bar work
- [ ] Panels display correctly
- [ ] Click outside closes
- [ ] Mobile tap behavior works

---

## Testing Requirements

### Unit Tests
- `CharacterSheet.test.tsx`: Renders all character data correctly
- `PanelOverlay.test.tsx`: Opens/closes, backdrop click works
- `KeyboardHint.test.tsx`: Visible/hidden states

### Integration Tests
- GamePage keyboard handling (may need to mock window.addEventListener)

### Manual Testing
1. Focus not on input → press `i` → inventory opens
2. Press `c` → inventory closes, character sheet opens
3. Press `Escape` → character sheet closes
4. Focus on chat input → press `i` → types "i" (shortcut disabled)
5. Click backpack icon → inventory opens
6. Click person icon → character sheet opens
7. Click outside panel → closes
8. Character sheet shows all 6 ability scores
9. Hint text visible when no panel open

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites
- Frontend running: `cd frontend && npm run dev`
- Browser DevTools open (Console tab)

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Press `i` (not in input) | Inventory panel opens in center | ☐ |
| 2 | Press `i` again | Inventory closes | ☐ |
| 3 | Press `c` | Character sheet opens | ☐ |
| 4 | Press `i` | Inventory opens, character sheet closes | ☐ |
| 5 | Press `Escape` | Panel closes | ☐ |
| 6 | Click backpack icon | Inventory opens | ☐ |
| 7 | Click backdrop | Panel closes | ☐ |
| 8 | Click person icon | Character sheet opens | ☐ |
| 9 | Verify character data | Shows name, class, level, HP, XP, gold, abilities | ☐ |
| 10 | Focus chat input, press `i` | Types "i", no panel opens | ☐ |
| 11 | Check hint text | Shows "I Inventory · C Character · Esc Close" at bottom | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| No character loaded | Navigate to game with invalid session | Normal error handling | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] Panels animate smoothly
- [ ] Icons are crisp at all zoom levels

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Missing character data | Session load failed | Panel shows placeholder or doesn't open |

### Edge Cases
- User holds modifier key + shortcut: Should not trigger (handled by check)
- Rapid key presses: State updates should be atomic
- Panel open during combat: Should still work, combat actions available
- Mobile without keyboard: Icons provide full functionality

---

## Cost Impact

### Claude API
- No impact - frontend-only change

### AWS
- No new resources
- No cost impact

---

## Open Questions

None - requirements are clear from the initial spec.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Requirements are explicit and well-defined |
| Feasibility | 10 | Simple frontend changes, no backend needed |
| Completeness | 9 | All aspects covered, minor styling decisions left to implementation |
| Alignment | 10 | Follows project patterns, no budget impact |
| **Overall** | **9.75** | High confidence - straightforward frontend feature |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated (zero)
- [x] Dependencies are listed (lucide-react)
- [x] Success criteria are measurable
