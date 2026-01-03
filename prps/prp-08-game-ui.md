# PRP-08: Game UI - Chat Interface

**Created**: 2026-01-02
**Initial**: `initials/init-08-game-ui.md`
**Status**: Ready

---

## Overview

### Problem Statement

The game page is currently a placeholder showing only the session ID. Players need a functional chat interface to interact with the AI Dungeon Master, see their character status, view combat information, and handle death scenarios.

### Proposed Solution

Replace the placeholder GamePage with a complete game UI featuring:
- Scrollable chat history with distinct DM/player message styling
- Character status bar (HP with color-coded bar, XP, Gold, Level)
- Combat status panel showing enemies during active combat
- Dice roll displays with visual styling for crits/fumbles
- Action input with Enter-to-send functionality
- Death screen overlay when character dies

### Success Criteria

- [ ] Chat history displays all messages from session
- [ ] Messages auto-scroll to bottom on new content
- [ ] Player can type and send actions (Enter sends, Shift+Enter for newline)
- [ ] DM responses appear with narrative text
- [ ] Dice rolls display with roll/modifier/total breakdown
- [ ] Character status bar shows HP/XP/Gold with HP color gradient
- [ ] Combat status shows living enemies during active combat
- [ ] Death screen appears when character dies
- [ ] Dead session blocks further input
- [ ] Mobile responsive (works on 375px width)
- [ ] Loading states for all async operations
- [ ] Error handling with user feedback

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Frontend tech stack (React + TypeScript + Tailwind)
- `docs/DECISIONS.md` - ADR-008 (React + Vite), ADR-005 (Anonymous sessions)
- `initials/init-04-frontend-shell.md` - Existing frontend structure
- `initials/init-06-action-handler.md` - Backend action endpoint

### Dependencies

- **Required**:
  - `init-04-frontend-shell` - React app structure, routing, API services
  - `init-06-action-handler` - POST /sessions/{id}/action endpoint
  - `init-07-combat-system` - Server-side combat, dice rolls in response
- **Optional**: None

### Files to Modify/Create

```
frontend/src/
├── pages/
│   └── GamePage.tsx                    # REWRITE: Full game UI
├── components/
│   └── game/
│       ├── index.ts                    # NEW: Barrel export
│       ├── ChatHistory.tsx             # NEW: Scrollable message list
│       ├── ChatMessage.tsx             # NEW: Message bubble with dice rolls
│       ├── DiceRoll.tsx                # NEW: Single dice roll display
│       ├── StateChangeSummary.tsx      # NEW: HP/Gold/XP delta display
│       ├── CharacterStatus.tsx         # NEW: Top status bar
│       ├── CombatStatus.tsx            # NEW: Enemy list during combat
│       ├── ActionInput.tsx             # NEW: Text input + send button
│       └── DeathScreen.tsx             # NEW: Game over overlay
├── hooks/
│   └── useGameSession.ts               # NEW: Game state management hook
├── services/
│   └── sessions.ts                     # MODIFY: Add sendAction method
└── types/
    └── index.ts                        # MODIFY: Add game UI types
```

---

## Technical Specification

### Type Definitions

Add to `frontend/src/types/index.ts`:

```typescript
/** Dice roll from server */
export interface DiceRoll {
  type: string;
  roll: number;
  modifier: number;
  total: number;
  success: boolean | null;
}

/** State changes from action response */
export interface StateChanges {
  hp_delta: number;
  gold_delta: number;
  xp_delta: number;
  location: string | null;
  inventory_add: string[];
  inventory_remove: string[];
  world_state: Record<string, unknown>;
}

/** Enemy in combat */
export interface CombatEnemy {
  id?: string;
  name: string;
  hp: number;
  max_hp: number;
  ac: number;
}

/** Character snapshot from action response */
export interface CharacterSnapshot {
  hp: number;
  max_hp: number;
  xp: number;
  gold: number;
  level: number;
  inventory: string[];
}

/** Full action response from server */
export interface FullActionResponse {
  narrative: string;
  state_changes: StateChanges;
  dice_rolls: DiceRoll[];
  combat_active: boolean;
  enemies: CombatEnemy[];
  character: CharacterSnapshot;
  character_dead: boolean;
  session_ended: boolean;
}

/** Extended message for game UI (includes dice rolls) */
export interface GameMessage extends Message {
  dice_rolls?: DiceRoll[];
  state_changes?: StateChanges;
}
```

### API Service Addition

Add to `frontend/src/services/sessions.ts`:

```typescript
/**
 * Send a player action to the DM.
 */
sendAction: (sessionId: string, action: string) =>
  request<FullActionResponse>(`/sessions/${sessionId}/action`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  }),
```

### Component Structure

```
components/game/
├── index.ts              # Export all game components
├── ChatHistory.tsx       # ~80 lines - scrollable message container
├── ChatMessage.tsx       # ~70 lines - single message with optional dice/state
├── DiceRoll.tsx          # ~50 lines - dice roll with crit/fumble styling
├── StateChangeSummary.tsx # ~40 lines - shows HP/Gold/XP changes
├── CharacterStatus.tsx   # ~80 lines - top bar with HP bar
├── CombatStatus.tsx      # ~50 lines - enemy list
├── ActionInput.tsx       # ~60 lines - textarea + send button
└── DeathScreen.tsx       # ~70 lines - game over overlay
```

---

## Implementation Steps

### Step 1: Add Type Definitions

**Files**: `frontend/src/types/index.ts`

Add the new types for `DiceRoll`, `StateChanges`, `CombatEnemy`, `CharacterSnapshot`, `FullActionResponse`, and `GameMessage` as shown in the Technical Specification.

**Validation**:
- [ ] TypeScript compiles without errors
- [ ] Types match backend models in `lambdas/dm/models.py`

---

### Step 2: Add sendAction to Session Service

**Files**: `frontend/src/services/sessions.ts`

Add the `sendAction` method to the session service.

**Validation**:
- [ ] TypeScript compiles without errors

---

### Step 3: Create useGameSession Hook

**Files**: `frontend/src/hooks/useGameSession.ts`, `frontend/src/hooks/index.ts`

Create the hook that manages:
- Loading session and character on mount
- Tracking messages state
- Sending actions with optimistic updates
- Updating character state from responses
- Detecting session ended / character death

Key features:
- Optimistically add player message before API call
- Rollback on error
- Update character snapshot from response

**Validation**:
- [ ] Hook compiles without errors
- [ ] Export added to hooks/index.ts

---

### Step 4: Create DiceRoll Component

**Files**: `frontend/src/components/game/DiceRoll.tsx`

Display a single dice roll with:
- Roll type label
- Natural roll value (highlight 20 as gold, 1 as red)
- Modifier with +/- sign
- Total
- Success/fail indicator for attacks

Styling:
- Critical (20): Gold background/border
- Fumble (1): Red background/border
- Normal: Gray

**Validation**:
- [ ] Component renders correctly
- [ ] Crit/fumble styling works

---

### Step 5: Create StateChangeSummary Component

**Files**: `frontend/src/components/game/StateChangeSummary.tsx`

Show state changes in a compact format:
- HP change: green for heal, red for damage
- Gold change: yellow for gain, gray for loss
- XP gain: blue
- Only show non-zero values

**Validation**:
- [ ] Component renders correctly
- [ ] Correct colors for positive/negative

---

### Step 6: Create ChatMessage Component

**Files**: `frontend/src/components/game/ChatMessage.tsx`

Single message bubble with:
- Header showing role ("Dungeon Master" or "You")
- Message content with preserved whitespace
- Dice rolls section (if any)
- State changes section (if any)

Styling:
- DM messages: Left-aligned, amber border
- Player messages: Right-aligned or different styling
- Timestamps (optional, can be hover tooltip)

**Validation**:
- [ ] DM vs Player styling correct
- [ ] Dice rolls render when present
- [ ] State changes render when present

---

### Step 7: Create ChatHistory Component

**Files**: `frontend/src/components/game/ChatHistory.tsx`

Scrollable container with:
- Auto-scroll to bottom on new messages (smooth)
- Loading indicator at bottom when waiting for response
- Flex column layout with gap between messages

**Validation**:
- [ ] Scrolls properly
- [ ] Auto-scroll works on new messages

---

### Step 8: Create CharacterStatus Component

**Files**: `frontend/src/components/game/CharacterStatus.tsx`

Top status bar showing:
- Character name, class, level
- HP bar with percentage-based color:
  - > 50%: green
  - 25-50%: yellow
  - < 25%: red
- Numeric HP display
- XP value
- Gold value

Responsive: Stack on mobile if needed

**Validation**:
- [ ] HP bar colors correctly
- [ ] Values display correctly
- [ ] Responsive on mobile

---

### Step 9: Create CombatStatus Component

**Files**: `frontend/src/components/game/CombatStatus.tsx`

Combat panel showing:
- "IN COMBAT" header with warning styling
- List of enemies with name, HP/max_hp, AC
- Only show living enemies (hp > 0)
- Hide when not in combat

**Validation**:
- [ ] Shows only in combat
- [ ] Displays enemy stats correctly
- [ ] Filters dead enemies

---

### Step 10: Create ActionInput Component

**Files**: `frontend/src/components/game/ActionInput.tsx`

Input form with:
- Textarea (2-3 rows, expandable)
- Send button (disabled when empty or loading)
- Enter to submit, Shift+Enter for newline
- Max length 500 chars
- Placeholder text

**Validation**:
- [ ] Enter submits, Shift+Enter adds newline
- [ ] Disabled during loading
- [ ] Clears after submit

---

### Step 11: Create DeathScreen Component

**Files**: `frontend/src/components/game/DeathScreen.tsx`

Full-screen overlay showing:
- Death message with character name
- Final stats (level, XP, gold)
- Buttons to create new character or go to character list
- Dark/dramatic styling

**Validation**:
- [ ] Overlay covers screen
- [ ] Navigation buttons work

---

### Step 12: Create Barrel Export

**Files**: `frontend/src/components/game/index.ts`

Export all game components from single index file.

**Validation**:
- [ ] All components exported

---

### Step 13: Rewrite GamePage

**Files**: `frontend/src/pages/GamePage.tsx`

Complete rewrite using:
- useGameSession hook
- All game components
- Loading state on initial load
- Error display
- Death screen when session ended

Layout:
- CharacterStatus at top (sticky)
- ChatHistory in middle (scrollable)
- CombatStatus above input (when in combat)
- ActionInput at bottom (sticky)

**Validation**:
- [ ] Page loads session correctly
- [ ] All components render
- [ ] Actions send and display correctly
- [ ] Death screen shows on character death

---

### Step 14: Write Unit Tests

**Files**:
- `frontend/src/components/game/DiceRoll.test.tsx`
- `frontend/src/components/game/CharacterStatus.test.tsx`
- `frontend/src/components/game/ChatMessage.test.tsx`
- `frontend/src/hooks/useGameSession.test.ts`

Test cases:
- DiceRoll: crit/fumble styling, modifier display
- CharacterStatus: HP percentage colors
- ChatMessage: DM vs player styling, dice rolls rendering
- useGameSession: message updates, error handling

**Validation**:
- [ ] All tests pass
- [ ] Good coverage of edge cases

---

## Testing Requirements

### Unit Tests

- `DiceRoll.test.tsx`: Natural 20 shows crit styling, natural 1 shows fumble styling
- `CharacterStatus.test.tsx`: HP bar color changes at thresholds (50%, 25%)
- `ChatMessage.test.tsx`: DM messages have amber border, player messages distinct
- `DeathScreen.test.tsx`: Displays final stats, navigation buttons work
- `useGameSession.test.ts`: Loads session, sends action, handles errors

### Integration Tests

- Full flow: Load game → Send action → See response → Check character update
- Combat flow: Send attack → See dice rolls → See enemy HP change
- Death flow: Character dies → Death screen appears → Can navigate away

### Manual Testing

1. Load game page with existing session
2. Verify message history displays correctly
3. Type action and press Enter
4. Verify action appears immediately (optimistic)
5. Verify DM response appears after loading
6. Verify dice rolls display in combat
7. Verify HP/XP/Gold update after action
8. Verify combat status shows during combat
9. Die in combat → verify death screen
10. Test on mobile viewport (375px width)

---

## Integration Test Plan

### Prerequisites

- Backend deployed: `cd cdk && cdk deploy --all`
- Frontend running: `cd frontend && npm run dev`
- Browser DevTools open (Console + Network tabs)
- Existing session with some message history

### Test Steps

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Navigate to /game/{sessionId} | Game page loads with character status | - |
| 2 | Check message history | Previous messages display correctly | - |
| 3 | Type "I attack the goblin" and press Enter | Message appears, input clears, loading shows | - |
| 4 | Wait for response | DM response appears with narrative | - |
| 5 | Check dice rolls (if combat) | Dice rolls show with d20(X)+Y = Z format | - |
| 6 | Check character status | HP/XP/Gold updated from response | - |
| 7 | Verify combat status (if in combat) | Enemy list shows with HP | - |
| 8 | Send action that kills character | Death screen appears | - |
| 9 | Click "Create New Character" | Navigates to /characters/new | - |
| 10 | Test on mobile (375px) | Layout responsive, no horizontal scroll | - |

### Error Scenarios

| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Session not found | Navigate to invalid session ID | Error message displayed | - |
| Network error | Disconnect network, send action | Error toast, input re-enabled | - |
| Session ended | Send action to ended session | Redirect to death screen or error | - |

### Browser Checks

- [ ] No CORS errors in Console
- [ ] No JavaScript errors in Console
- [ ] API requests include X-User-Id header
- [ ] POST /sessions/{id}/action returns 200
- [ ] Response body matches FullActionResponse type

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| 404 Session not found | Invalid session ID | Show error, link to characters |
| 400 Session ended | Session already ended | Show death screen |
| Network error | Connection failed | Show toast, re-enable input |
| 500 Server error | Backend issue | Show error message |

### Edge Cases

- Empty message history on new session (show welcome message or nothing)
- Very long narrative response (should scroll, not break layout)
- Rapid action sending (disable input during request)
- Session loaded but character deleted (show error)
- Combat ends mid-response (transition out of combat state)

---

## Cost Impact

### Claude API

- No additional impact - existing action endpoint already calls Claude
- Frontend UI only consumes existing API

### AWS

- No new resources
- No additional cost impact

---

## Open Questions

1. ~~Should we show timestamps on messages?~~ **Decision**: No timestamps for cleaner UI, can add later
2. ~~What happens if session loads but character was deleted?~~ **Decision**: Show error and link to characters
3. Should we add a "retry" button for failed actions? **Decision**: Yes, remove failed message and re-enable input

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Initial spec is very detailed with component specs |
| Feasibility | 9 | Straightforward React components, no complex state |
| Completeness | 9 | All components specified, types match backend |
| Alignment | 9 | Uses existing patterns, Tailwind, mobile-first |
| **Overall** | **9** | High confidence - well-defined frontend feature |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated (none)
- [x] Dependencies are listed
- [x] Success criteria are measurable
- [x] Integration test plan included
