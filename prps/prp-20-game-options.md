# PRP-20: Game Options

**Created**: 2026-01-18
**Initial**: `initials/init-20-game-options.md`
**Status**: Draft

---

## Overview

### Problem Statement

Players currently have no control over their gameplay experience preferences. The game is mature-rated (18+) but different players have different comfort levels with:
- Gore and violence descriptions
- Mature/sexual content detail
- Accidentally attacking friendly NPCs

Without options, all players get the same experience, which may not match their preferences.

### Proposed Solution

Add a game options system with three initial settings:
1. **Confirm Combat (Non-Hostiles)** - Server-side confirmation before attacking non-hostile NPCs
2. **Gore Level** - Control violence description intensity (Mild/Standard/Extreme)
3. **Mature Content Level** - Control romantic/sexual content detail (Fade to Black/Suggestive/Explicit)

Options are stored per-session and passed to the DM in dynamic context to adjust narrative style.

### Success Criteria

- [ ] Options UI accessible via gear icon and 'O' keyboard shortcut
- [ ] Options persist in session (survive page refresh)
- [ ] Gore level affects violence descriptions in DM responses
- [ ] Mature content level affects romantic/sexual scene descriptions
- [ ] Combat confirmation prevents accidental attacks on non-hostiles
- [ ] All options have sensible defaults (ON, Standard, Suggestive)

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Architecture overview (session model, API structure)
- `docs/DECISIONS.md` - ADR-007 (Mature content approach), ADR-009 (Mistral Small)
- `lambdas/dm/prompts/context.py` - Dynamic context builder pattern
- `lambdas/shared/actions.py` - Action detection patterns

### Dependencies

- Required: None (builds on existing session and DM infrastructure)
- Optional: None

### Files to Modify/Create

```
# Backend - Models
lambdas/shared/models.py                    # Add GameOptions, PendingCombatConfirmation models

# Backend - Session
lambdas/session/handler.py                  # Add PATCH /sessions/{id}/options endpoint
lambdas/session/service.py                  # Add update_options method

# Backend - DM
lambdas/shared/actions.py                   # Add attack intent detection functions
lambdas/dm/prompts/context.py               # Add options context section
lambdas/dm/service.py                       # Add hostility check, pending confirmation logic

# Frontend - Types
frontend/src/types/index.ts                 # Add GameOptions, PendingConfirmation types

# Frontend - Components
frontend/src/components/game/OptionsPanel.tsx    # New component
frontend/src/components/game/index.ts            # Export OptionsPanel

# Frontend - Pages
frontend/src/pages/GamePage.tsx             # Add options state, 'O' shortcut, gear icon

# Frontend - Services
frontend/src/services/session.ts            # Add updateOptions API call
```

---

## Technical Specification

### Data Models

**Backend (Python/Pydantic)**:
```python
class GoreLevel(str, Enum):
    MILD = "mild"
    STANDARD = "standard"
    EXTREME = "extreme"

class MatureContentLevel(str, Enum):
    FADE_TO_BLACK = "fade_to_black"
    SUGGESTIVE = "suggestive"
    EXPLICIT = "explicit"

class GameOptions(BaseModel):
    """Player game options stored in session."""
    confirm_combat_noncombat: bool = True
    gore_level: GoreLevel = GoreLevel.STANDARD
    mature_content: MatureContentLevel = MatureContentLevel.SUGGESTIVE

class PendingCombatConfirmation(BaseModel):
    """Pending attack confirmation for non-hostile target."""
    target: str                    # "shopkeeper", "the guard", etc.
    original_action: str           # Player's original input
    reason: str = "non-hostile"    # Why confirmation needed
    created_at: str                # ISO timestamp
```

**Frontend (TypeScript)**:
```typescript
type GoreLevel = 'mild' | 'standard' | 'extreme';
type MatureContentLevel = 'fade_to_black' | 'suggestive' | 'explicit';

interface GameOptions {
  confirm_combat_noncombat: boolean;
  gore_level: GoreLevel;
  mature_content: MatureContentLevel;
}

interface PendingCombatConfirmation {
  target: string;
  original_action: string;
  reason: string;
}
```

### API Changes

| Method | Path | Request | Response |
|--------|------|---------|----------|
| PATCH | /sessions/{id}/options | `GameOptions` | `{ options: GameOptions }` |

### Session Model Extension

Add to Session model:
```python
class Session(BaseModel):
    # ... existing fields ...
    options: GameOptions = Field(default_factory=GameOptions)
    pending_combat_confirmation: PendingCombatConfirmation | None = None
```

---

## Implementation Steps

### Step 1: Add GameOptions and PendingCombatConfirmation Models

**Files**: `lambdas/shared/models.py`

Add the new enums and models after the existing classes:

```python
class GoreLevel(str, Enum):
    """Gore level preference."""
    MILD = "mild"
    STANDARD = "standard"
    EXTREME = "extreme"

class MatureContentLevel(str, Enum):
    """Mature content preference."""
    FADE_TO_BLACK = "fade_to_black"
    SUGGESTIVE = "suggestive"
    EXPLICIT = "explicit"

class GameOptions(BaseModel):
    """Player game options stored in session."""
    confirm_combat_noncombat: bool = True
    gore_level: GoreLevel = GoreLevel.STANDARD
    mature_content: MatureContentLevel = MatureContentLevel.SUGGESTIVE

class PendingCombatConfirmation(BaseModel):
    """Pending attack confirmation for non-hostile target."""
    target: str
    original_action: str
    reason: str = "non-hostile"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
```

Update Session model to include:
```python
options: GameOptions = Field(default_factory=GameOptions)
pending_combat_confirmation: PendingCombatConfirmation | None = None
```

Update `from_db_item` and `to_db_item` to handle the new fields.

**Validation**:
- [ ] Model imports successfully
- [ ] Default values are correct
- [ ] Existing tests still pass

### Step 2: Add Attack Intent Detection

**Files**: `lambdas/shared/actions.py`

Add attack intent detection patterns and functions:

```python
# Patterns to detect attack intent
ATTACK_PATTERNS = [
    r"\battack\b",
    r"\bstrike\b",
    r"\bstab\b",
    r"\bkill\b",
    r"\bhit\b",
    r"\bpunch\b",
    r"\bkick\b",
    r"\bslash\b",
    r"\bshoot\b",
    r"\bswing\b.*\bat\b",
    r"\bsword\b.*\bat\b",
    r"\bblade\b.*\binto\b",
    r"\barrow\b.*\bat\b",
]

# Confirmation response patterns
CONFIRM_PATTERNS = [
    r"\byes\b",
    r"\byeah\b",
    r"\byep\b",
    r"\bsure\b",
    r"\bdo\s+it\b",
    r"\bproceed\b",
    r"\bconfirm\b",
]

CANCEL_PATTERNS = [
    r"\bno\b",
    r"\bnope\b",
    r"\bnevermind\b",
    r"\bcancel\b",
    r"\bstop\b",
    r"\bwait\b",
    r"\bdon'?t\b",
]

def is_attack_action(action: str) -> bool:
    """Detect if player action is an attack attempt."""
    action_lower = action.lower()
    for pattern in ATTACK_PATTERNS:
        if re.search(pattern, action_lower):
            return True
    return False

def extract_attack_target(action: str) -> str | None:
    """Extract the target from an attack action (best effort)."""
    # Match patterns like "attack the shopkeeper", "stab him", "kill the guard"
    patterns = [
        r"(?:attack|strike|stab|kill|hit|punch|kick|slash|shoot)\s+(?:the\s+)?(.+?)(?:\s+with|\s*$)",
        r"(?:swing|sword|blade|arrow)\s+(?:at|into)\s+(?:the\s+)?(.+?)(?:\s+with|\s*$)",
    ]
    action_lower = action.lower()
    for pattern in patterns:
        match = re.search(pattern, action_lower)
        if match:
            return match.group(1).strip()
    return None

def detect_confirmation_response(action: str) -> str:
    """Detect if action is a confirmation, cancellation, or new action.

    Returns:
        "confirm" - Player confirmed the pending action
        "cancel" - Player cancelled
        "new_action" - This is a different action, clear pending state
    """
    action_lower = action.lower()

    # Check for explicit confirmation
    for pattern in CONFIRM_PATTERNS:
        if re.search(pattern, action_lower):
            return "confirm"

    # Check for cancellation
    for pattern in CANCEL_PATTERNS:
        if re.search(pattern, action_lower):
            return "cancel"

    # Check if this is another attack (counts as confirm)
    if is_attack_action(action):
        return "confirm"

    # Otherwise treat as new action
    return "new_action"
```

**Validation**:
- [ ] Attack detection works for common phrases
- [ ] Target extraction handles "attack the shopkeeper"
- [ ] Confirmation detection differentiates yes/no/other

### Step 3: Add Options Context to DM Prompt

**Files**: `lambdas/dm/prompts/context.py`

Add method to format options context:

```python
def _format_options_context(self, options: "GameOptions") -> str:
    """Format player options for DM context.

    Args:
        options: Player's game options

    Returns:
        Formatted options context block
    """
    gore_instructions = {
        "mild": "MILD: Describe violence outcomes without graphic detail. 'You defeat him' not 'blood sprays'.",
        "standard": "STANDARD: Moderate gore, visceral but not excessive. Blood, wounds, death described.",
        "extreme": "EXTREME: Full graphic detail. Describe injuries, gore, viscera explicitly.",
    }

    mature_instructions = {
        "fade_to_black": "FADE_TO_BLACK: Cut away from romantic/sexual scenes. 'The night passes...'",
        "suggestive": "SUGGESTIVE: Sensual descriptions, tension, but no explicit acts.",
        "explicit": "EXPLICIT: Full adult content permitted, describe acts explicitly.",
    }

    lines = [
        "## PLAYER OPTIONS",
        f"- Gore level: {options.gore_level.value.upper()}",
        f"- Mature content: {options.mature_content.value.upper()}",
        "",
        "Adjust your narration style according to these preferences:",
        "",
        f"GORE: {gore_instructions[options.gore_level.value]}",
        f"MATURE: {mature_instructions[options.mature_content.value]}",
    ]

    return "\n".join(lines)

def _format_pending_confirmation(self, pending: "PendingCombatConfirmation") -> str:
    """Format pending combat confirmation context.

    Args:
        pending: Pending confirmation state

    Returns:
        Context block instructing DM to ask for confirmation
    """
    return f"""## PENDING COMBAT CONFIRMATION
The player wants to attack "{pending.target}", but they are non-hostile.
Ask the player to confirm: describe the target, note they're not threatening,
ask "Are you sure you want to attack?"
Do NOT initiate combat. Wait for player's response."""
```

Update `build_context` to include options:

```python
def build_context(
    self,
    character: Character,
    session: Session,
    session_data: dict | None = None,
    action: str = "",
    options: "GameOptions | None" = None,
    pending_confirmation: "PendingCombatConfirmation | None" = None,
) -> str:
    parts = [
        self._format_character_block(character),
        self._format_world_state(session),
        self._format_message_history(session.message_history),
    ]

    # Add options context
    if options:
        parts.append(self._format_options_context(options))

    # Add pending confirmation context (takes priority)
    if pending_confirmation:
        parts.append(self._format_pending_confirmation(pending_confirmation))

    # ... rest of existing context building
```

**Validation**:
- [ ] Options context formatted correctly
- [ ] Pending confirmation context formatted correctly
- [ ] build_context signature updated

### Step 4: Add Hostility Classification

**Files**: `lambdas/dm/service.py`

Add a lightweight method to ask the DM about target hostility:

```python
HOSTILITY_CHECK_PROMPT = """Based on the current scene, is "{target}" currently hostile toward the player?
Consider: Have they attacked? Threatened? Are they an enemy combatant?
Being unfriendly, rude, or an obstacle is NOT hostile.
Reply with ONLY one word: HOSTILE or NON_HOSTILE"""

async def _check_target_hostility(self, target: str, session: Session, character: Character) -> bool:
    """Ask the DM to classify target hostility.

    Args:
        target: The target name/description
        session: Current session for context
        character: Current character for context

    Returns:
        True if target is hostile, False otherwise
    """
    # Build minimal context for hostility check
    context = self.prompt_builder.build_context(character, session)
    prompt = HOSTILITY_CHECK_PROMPT.format(target=target)

    ai_client = self._get_ai_client()
    response = ai_client.send_action(
        system_prompt="You are a classifier. Answer only HOSTILE or NON_HOSTILE.",
        context=context,
        action=prompt,
    )

    # Parse response - default to NON_HOSTILE if unclear (safer)
    response_text = response.text.strip().upper()
    return "HOSTILE" in response_text
```

**Validation**:
- [ ] Hostility check returns boolean
- [ ] Defaults to NON_HOSTILE on ambiguous response
- [ ] Token usage is minimal (~100 tokens)

### Step 5: Update DM Service for Combat Confirmation

**Files**: `lambdas/dm/service.py`

Update `process_action` to handle combat confirmation flow:

```python
def process_action(self, user_id: str, session_id: str, action: str, ...) -> ActionResponse:
    # ... existing session/character loading ...

    # Load options from session
    options = session_data.get("options", {})
    game_options = GameOptions(**options) if options else GameOptions()

    # Check for pending confirmation
    pending = session_data.get("pending_combat_confirmation")
    if pending:
        pending_confirmation = PendingCombatConfirmation(**pending)
        response_type = detect_confirmation_response(action)

        if response_type == "confirm":
            # Clear pending and process original action
            self._clear_pending_confirmation(user_id, session_id)
            action = pending_confirmation.original_action
            # Fall through to normal processing
        elif response_type == "cancel":
            # Clear pending, narrate cancellation
            self._clear_pending_confirmation(user_id, session_id)
            return self._narrate_action_cancelled(session, character, pending_confirmation)
        else:
            # New action - clear pending and process new action
            self._clear_pending_confirmation(user_id, session_id)
            # Fall through with new action

    # Check if this is an attack on a potentially non-hostile target
    if (game_options.confirm_combat_noncombat
        and is_attack_action(action)
        and not combat_active):

        target = extract_attack_target(action)
        if target:
            is_hostile = self._check_target_hostility(target, session, character)
            if not is_hostile:
                # Set pending confirmation and return confirmation request
                self._set_pending_confirmation(user_id, session_id, target, action)
                return self._request_combat_confirmation(session, character, target, options)

    # ... continue with normal action processing ...
```

**Validation**:
- [ ] Confirmation flow works end-to-end
- [ ] Pending state persists in session
- [ ] Cancellation clears state correctly

### Step 6: Add Session Options API Endpoint

**Files**: `lambdas/session/handler.py`, `lambdas/session/service.py`

Add PATCH endpoint for updating options:

```python
# In handler.py
@app.patch("/sessions/<session_id>/options")
@tracer.capture_method
def update_options(session_id: str) -> dict[str, Any]:
    """Update session options.

    Args:
        session_id: The session's ID

    Returns:
        200 response with updated options
    """
    user_id = get_user_id()

    try:
        body = app.current_event.json_body or {}
        options = GameOptions(**body)
    except ValidationError as e:
        raise BadRequestError(str(e)) from None

    try:
        return get_service().update_options(user_id, session_id, options)
    except NotFoundError:
        raise APINotFoundError("Session not found") from None

# In service.py
def update_options(self, user_id: str, session_id: str, options: GameOptions) -> dict:
    """Update session options.

    Args:
        user_id: User ID
        session_id: Session ID
        options: New options values

    Returns:
        Dict with updated options
    """
    pk = f"USER#{user_id}"
    sk = f"SESS#{session_id}"

    # Verify session exists
    item = self.db.get_item(pk, sk)
    if not item:
        raise NotFoundError(f"Session {session_id} not found")

    # Update options
    self.db.update_item(pk, sk, {"options": options.model_dump()})

    return {"options": options.model_dump()}
```

**Validation**:
- [ ] PATCH endpoint returns 200 with options
- [ ] 404 if session not found
- [ ] 400 if invalid options values

### Step 7: Add Frontend Types

**Files**: `frontend/src/types/index.ts`

Add the TypeScript types:

```typescript
/** Gore level preference */
export type GoreLevel = 'mild' | 'standard' | 'extreme';

/** Mature content preference */
export type MatureContentLevel = 'fade_to_black' | 'suggestive' | 'explicit';

/** Game options stored in session */
export interface GameOptions {
  confirm_combat_noncombat: boolean;
  gore_level: GoreLevel;
  mature_content: MatureContentLevel;
}

/** Pending combat confirmation state */
export interface PendingCombatConfirmation {
  target: string;
  original_action: string;
  reason: string;
}
```

**Validation**:
- [ ] Types compile without errors
- [ ] Types match backend models

### Step 8: Add Session API updateOptions

**Files**: `frontend/src/services/session.ts`

Add the updateOptions API call:

```typescript
/**
 * Update session options.
 */
export async function updateOptions(
  sessionId: string,
  options: GameOptions
): Promise<{ options: GameOptions }> {
  return fetchApi<{ options: GameOptions }>(
    `/sessions/${sessionId}/options`,
    {
      method: 'PATCH',
      body: JSON.stringify(options),
    }
  );
}
```

**Validation**:
- [ ] API call uses PATCH method
- [ ] Returns updated options

### Step 9: Create OptionsPanel Component

**Files**: `frontend/src/components/game/OptionsPanel.tsx`

Create the options panel UI:

```typescript
import { Settings } from 'lucide-react';
import { GameOptions, GoreLevel, MatureContentLevel } from '../../types';

interface OptionsPanelProps {
  options: GameOptions;
  onOptionsChange: (options: GameOptions) => void;
  isLoading?: boolean;
}

const GORE_LABELS: Record<GoreLevel, string> = {
  mild: 'Mild',
  standard: 'Standard',
  extreme: 'Extreme',
};

const MATURE_LABELS: Record<MatureContentLevel, string> = {
  fade_to_black: 'Fade to Black',
  suggestive: 'Suggestive',
  explicit: 'Explicit',
};

export function OptionsPanel({ options, onOptionsChange, isLoading }: OptionsPanelProps) {
  const handleToggle = (key: keyof GameOptions) => {
    if (typeof options[key] === 'boolean') {
      onOptionsChange({ ...options, [key]: !options[key] });
    }
  };

  const handleSelect = (key: keyof GameOptions, value: string) => {
    onOptionsChange({ ...options, [key]: value });
  };

  return (
    <div className="p-4 space-y-6">
      {/* Confirm Combat Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-white font-medium">Confirm Combat (Non-Hostiles)</div>
          <div className="text-gray-400 text-sm">Ask before attacking friendly NPCs</div>
        </div>
        <button
          onClick={() => handleToggle('confirm_combat_noncombat')}
          disabled={isLoading}
          className={`w-12 h-6 rounded-full transition-colors ${
            options.confirm_combat_noncombat ? 'bg-amber-500' : 'bg-gray-600'
          }`}
        >
          <div
            className={`w-5 h-5 bg-white rounded-full transition-transform ${
              options.confirm_combat_noncombat ? 'translate-x-6' : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>

      {/* Gore Level Select */}
      <div>
        <div className="text-white font-medium mb-2">Gore Level</div>
        <div className="flex gap-2">
          {(['mild', 'standard', 'extreme'] as GoreLevel[]).map((level) => (
            <button
              key={level}
              onClick={() => handleSelect('gore_level', level)}
              disabled={isLoading}
              className={`flex-1 py-2 px-3 rounded transition-colors ${
                options.gore_level === level
                  ? 'bg-amber-500 text-black'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {GORE_LABELS[level]}
            </button>
          ))}
        </div>
      </div>

      {/* Mature Content Select */}
      <div>
        <div className="text-white font-medium mb-2">Mature Content</div>
        <div className="flex gap-2">
          {(['fade_to_black', 'suggestive', 'explicit'] as MatureContentLevel[]).map((level) => (
            <button
              key={level}
              onClick={() => handleSelect('mature_content', level)}
              disabled={isLoading}
              className={`flex-1 py-2 px-3 rounded text-sm transition-colors ${
                options.mature_content === level
                  ? 'bg-amber-500 text-black'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {MATURE_LABELS[level]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

Export from index:
```typescript
export { OptionsPanel } from './OptionsPanel';
```

**Validation**:
- [ ] Component renders without errors
- [ ] Toggle changes boolean value
- [ ] Select buttons change string value

### Step 10: Integrate Options into GamePage

**Files**: `frontend/src/pages/GamePage.tsx`

Add options state, keyboard shortcut, and gear icon:

```typescript
import { Package, User, Settings } from 'lucide-react';
import { OptionsPanel } from '../components/game';
import { updateOptions } from '../services/session';
import { GameOptions } from '../types';

// Update PanelType
type PanelType = 'inventory' | 'character' | 'options' | null;

// In component:
const [options, setOptions] = useState<GameOptions>({
  confirm_combat_noncombat: true,
  gore_level: 'standard',
  mature_content: 'suggestive',
});

// Load options from session
useEffect(() => {
  if (session?.options) {
    setOptions(session.options);
  }
}, [session]);

// Handle options change
const handleOptionsChange = useCallback(async (newOptions: GameOptions) => {
  setOptions(newOptions);
  if (sessionId) {
    try {
      await updateOptions(sessionId, newOptions);
    } catch (error) {
      console.error('Failed to save options:', error);
    }
  }
}, [sessionId]);

// Add 'o' keyboard shortcut in useEffect
case 'o':
  e.preventDefault();
  setActivePanel((prev) => (prev === 'options' ? null : 'options'));
  break;

// Add gear icon to CharacterStatus or status bar
<button onClick={() => setActivePanel('options')} className="...">
  <Settings size={18} />
</button>

// Add Options Panel Overlay
<PanelOverlay
  isOpen={activePanel === 'options'}
  onClose={closePanel}
  title="Options"
  icon={<Settings size={20} />}
>
  <OptionsPanel
    options={options}
    onOptionsChange={handleOptionsChange}
  />
</PanelOverlay>
```

**Validation**:
- [ ] 'O' key opens options panel
- [ ] Gear icon visible in status bar
- [ ] Options changes save to backend

### Step 11: Update KeyboardHint

**Files**: `frontend/src/components/game/KeyboardHint.tsx`

Add 'O' for options to the keyboard hints.

**Validation**:
- [ ] 'O - Options' shown in hints

### Step 12: Run Tests

**Files**: `lambdas/tests/`, `frontend/`

```bash
cd lambdas && .venv/bin/pytest
cd frontend && npm test
```

**Validation**:
- [ ] All backend tests pass
- [ ] All frontend tests pass

### Step 13: Deploy Backend

Deploy the updated Lambda functions:

```bash
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip

zip -r /tmp/sess-update.zip session/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-session --zip-file fileb:///tmp/sess-update.zip
```

**Validation**:
- [ ] DM Lambda deployed
- [ ] Session Lambda deployed

### Step 14: Deploy Frontend

```bash
cd frontend
# Bump version in package.json
npm run build
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

**Validation**:
- [ ] Frontend deployed
- [ ] CloudFront invalidation created

---

## Testing Requirements

### Unit Tests

```python
# Test attack intent detection
def test_is_attack_action():
    assert is_attack_action("I attack the guard") == True
    assert is_attack_action("I stab the shopkeeper") == True
    assert is_attack_action("I kill him") == True
    assert is_attack_action("I talk to the guard") == False
    assert is_attack_action("I look around") == False

def test_extract_attack_target():
    assert extract_attack_target("I attack the guard") == "guard"
    assert extract_attack_target("I stab the shopkeeper") == "shopkeeper"
    assert extract_attack_target("kill him") == "him"

def test_detect_confirmation_response():
    assert detect_confirmation_response("yes") == "confirm"
    assert detect_confirmation_response("Yeah, do it") == "confirm"
    assert detect_confirmation_response("no") == "cancel"
    assert detect_confirmation_response("nevermind") == "cancel"
    assert detect_confirmation_response("I look around") == "new_action"
    assert detect_confirmation_response("I attack him") == "confirm"

def test_game_options_defaults():
    opts = GameOptions()
    assert opts.confirm_combat_noncombat == True
    assert opts.gore_level == GoreLevel.STANDARD
    assert opts.mature_content == MatureContentLevel.SUGGESTIVE
```

### Integration Tests

- Options PATCH endpoint returns updated options
- Options persist across session reload
- DM context includes options when set

### Manual Testing

See Integration Test Plan below.

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites

- Backend deployed with new endpoints
- Frontend at chaos.jurigregg.com
- Existing game session available

### Test Steps

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Press 'O' key (not in input) | Options panel opens | ☐ |
| 2 | Click gear icon in status bar | Options panel opens | ☐ |
| 3 | Toggle "Confirm Combat" OFF then ON | Toggle animates, value changes | ☐ |
| 4 | Select "Extreme" gore level | Button highlights, others deselect | ☐ |
| 5 | Select "Explicit" mature content | Button highlights | ☐ |
| 6 | Refresh page | Options persist (same values) | ☐ |
| 7 | Set "Confirm Combat" ON, go to town | Find shopkeeper | ☐ |
| 8 | Type "I attack the shopkeeper" | DM asks "Are you sure?" | ☐ |
| 9 | Type "yes" | Combat initiates with shopkeeper | ☐ |
| 10 | New session, attack shopkeeper again | DM asks confirmation | ☐ |
| 11 | Type "no" or "nevermind" | No combat, can take other action | ☐ |
| 12 | Set "Confirm Combat" OFF | Toggle turns off | ☐ |
| 13 | Attack shopkeeper | Combat initiates immediately (no confirm) | ☐ |
| 14 | Set gore to "Mild", kill enemy | Violence description is mild | ☐ |
| 15 | Set gore to "Extreme", kill enemy | Violence description is graphic | ☐ |

### Error Scenarios

| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Invalid options value | Send invalid API request | 400 Bad Request | ☐ |
| Session not found | PATCH with wrong session ID | 404 Not Found | ☐ |
| Already in combat | Attack during combat | No confirmation needed | ☐ |

### Browser Checks

- [ ] No JavaScript errors in Console
- [ ] PATCH requests visible in Network tab
- [ ] Options saved correctly (check session API response)

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| ValidationError | Invalid option value | Return 400 with details |
| NotFoundError | Session doesn't exist | Return 404 |
| AI timeout | Hostility check times out | Default to NON_HOSTILE (safer) |

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Target extraction fails | Skip confirmation, process normally |
| Hostility check fails | Default to NON_HOSTILE, ask confirmation |
| Player in combat already | Skip confirmation (already fighting) |
| Multiple pending confirms | Only one at a time, new action clears old |

---

## Cost Impact

### Mistral API

**Hostility Classification Call**:
- Tokens per call: ~100 input + ~10 output = 110 tokens
- Frequency: Only when confirm=ON + attack detected + not in combat
- Estimated: 5-10 calls per session
- At 100 sessions/day, 10 calls each: 110K tokens/day
- Cost: ~$0.22/day additional = **~$6.60/month worst case**

In practice much lower (most attacks are against hostile enemies).

### AWS

- No new resources
- Slightly more DynamoDB read/writes for options
- Estimated: < $0.50/month additional

**Total estimated impact**: $1-7/month

---

## Open Questions

1. **Should hostility check be cached?** - If player attacks same target twice, should we skip the second check? (Answer: No, keep simple for now)

2. **What about group attacks?** - "I attack the guards" (plural). (Answer: Confirm once for the group)

3. **Timeout for pending confirmation?** - Should it expire? (Answer: No, keep until explicit action)

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements well-defined with UI and flow details |
| Feasibility | 8 | Builds on existing patterns; hostility check is new ground |
| Completeness | 8 | Covers main flows; some edge cases may emerge |
| Alignment | 9 | Improves UX, within budget, matches project patterns |
| **Overall** | **8.5** | High confidence; hostility check is the main uncertainty |

**Main risks**:
- Hostility classification accuracy depends on DM context
- Attack target extraction is regex-based (may miss some phrasings)
- Additional AI call adds latency and cost

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed (none)
- [x] Success criteria are measurable
