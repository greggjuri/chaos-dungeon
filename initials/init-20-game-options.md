# init-20-game-options.md (v2)

## Overview

Add a game options/settings system that allows players to customize their gameplay experience. Start with three core options that address player agency and content preferences.

## Initial Options

### 1. Confirm Combat (Non-Hostiles)
- **Default**: On
- **When On**: Before attacking a non-hostile NPC/creature, server intercepts and asks for confirmation
- **When Off**: Combat initiates immediately as before
- **Purpose**: Prevents accidental combat, gives player a moment to reconsider

### 2. Gore Level
- **Options**: Mild / Standard / Extreme
- **Default**: Standard
- **Mild**: Violence described but not graphically ("You strike him down")
- **Standard**: Moderate gore ("Blood sprays as your blade cuts deep")
- **Extreme**: Full graphic detail ("The blade cleaves through his skull, brain matter splattering...")
- **Purpose**: Player comfort preference

### 3. Mature Content Level
- **Options**: Fade to Black / Suggestive / Explicit
- **Default**: Suggestive
- **Fade to Black**: Scene cuts away ("You spend the night together. Morning comes...")
- **Suggestive**: Sensual but not explicit ("Her hands trace down your chest as you pull her close...")
- **Explicit**: Full adult content
- **Purpose**: Player preference for romantic/sexual scenes

---

## Technical Design

### Storage

Options stored in session document in DynamoDB:
```python
session.options = {
    "confirm_combat_noncombat": True,
    "gore_level": "standard",      # mild | standard | extreme
    "mature_content": "suggestive" # fade_to_black | suggestive | explicit
}
```

### Frontend
- New "Options" button/icon in status bar (gear icon)
- Options panel (similar to character sheet overlay)
- Press `o` keyboard shortcut to open
- Toggle/select controls for each option
- Changes save immediately to session

### Backend
- Options passed to DM in dynamic context
- DM prompt includes current option values
- DM adjusts narrative style based on gore/mature options
- **Combat confirmation handled server-side** (see below)

---

## Combat Confirmation Flow (Server-Side)

### Why Server-Side?

Based on our established pattern: **server controls game state, DM controls narrative**.

If we relied purely on the DM prompt to ask "Are you sure?", the DM would need authority to initiate combat when the player confirms - which violates our server authority principle. Instead, we handle confirmation at the server level.

### Hostility Detection

We don't have explicit hostility tracking for NPCs. Instead, we use a pragmatic approach:

**Ask the DM to classify the target** as part of action processing:

When processing an attack action and `confirm_combat_noncombat=true`:
1. Server detects attack intent (keywords: attack, strike, stab, kill, etc.)
2. Server asks DM: "Is [target] currently hostile toward the player? Reply HOSTILE or NON_HOSTILE only."
3. If NON_HOSTILE and not in active combat → enter pending confirmation state
4. If HOSTILE or already in combat → proceed normally

This is a lightweight classification call (~50 tokens) that leverages the DM's scene context.

### State Machine

```
Player: "I attack the shopkeeper"
    ↓
Server: Detect attack intent, extract target "shopkeeper"
    ↓
Server: Ask DM for hostility classification (if confirm_combat=ON)
    ↓
DM: "NON_HOSTILE"
    ↓
Server: Set session.pending_combat_confirmation = {
    target: "shopkeeper",
    original_action: "I attack the shopkeeper",
    reason: "non-hostile"
}
    ↓
Server: Instruct DM to narrate the pause
    ↓
DM: "The shopkeeper looks up from his wares, unaware of your intent. 
     He hasn't threatened you. Are you sure you want to attack?"
    ↓
[Response includes pending_confirmation flag for frontend]
    ↓
Player: "Yes" / "I attack" / any affirmative
    ↓
Server: Detect confirmation, clear pending state
    ↓
Server: Process original attack action normally (initiate combat)
```

### Cancellation

Player can cancel with:
- "No" / "Nevermind" / "I don't" / any negative
- Any non-combat action ("I look around", "I leave")

Server clears `pending_combat_confirmation` and processes the new action normally.

### Data Model Addition

```python
# In session model
class PendingCombatConfirmation(BaseModel):
    target: str                    # "shopkeeper", "the guard", etc.
    original_action: str           # Player's original input
    reason: str                    # "non-hostile"
    created_at: datetime           # For timeout (optional)

session.pending_combat_confirmation: PendingCombatConfirmation | None
```

### Detection Keywords

Attack intent detected by keywords in action:
- Primary: attack, strike, stab, kill, hit, punch, kick, slash, shoot
- Secondary with target: "sword at", "blade into", "arrow at"

This doesn't need to be perfect - false positives just mean an extra confirmation, which is fine.

### Confirmation Detection

Affirmative responses:
- "yes", "yeah", "yep", "sure", "do it", "attack", "proceed", "confirm"
- Repeating the attack: "I attack", "kill him", etc.

Negative responses:
- "no", "nope", "nevermind", "cancel", "stop", "wait", "don't"

Anything else: Treat as new action, clear pending state.

---

## DM Prompt Integration

### Options Context Section

Add to dynamic context (not system prompt - these change per-session):

```
## PLAYER OPTIONS
- Gore level: [MILD/STANDARD/EXTREME]
- Mature content: [FADE_TO_BLACK/SUGGESTIVE/EXPLICIT]

Adjust your narration style according to these preferences:

GORE LEVEL:
- MILD: Describe violence outcomes without graphic detail. "You defeat him" not "blood sprays"
- STANDARD: Moderate gore, visceral but not excessive. Blood, wounds, death described.
- EXTREME: Full graphic detail. Describe injuries, gore, viscera explicitly.

MATURE CONTENT:
- FADE_TO_BLACK: Cut away from romantic/sexual scenes. "The night passes..." 
- SUGGESTIVE: Sensual descriptions, tension, but no explicit acts
- EXPLICIT: Full adult content permitted, describe acts explicitly
```

### Combat Confirmation Prompt

When `pending_combat_confirmation` is set, add to context:

```
## PENDING COMBAT CONFIRMATION
The player wants to attack [target], but you've identified them as non-hostile.
Ask the player to confirm: describe the target, note they're not threatening, 
ask "Are you sure you want to attack?"
Do NOT initiate combat. Wait for player's response.
```

### Hostility Classification Prompt

Lightweight prompt for classification call:

```
Based on the current scene, is [target] currently hostile toward the player?
Consider: Have they attacked? Threatened? Are they an enemy combatant?
Being unfriendly, rude, or an obstacle is NOT hostile.
Reply with ONLY one word: HOSTILE or NON_HOSTILE
```

---

## Files to Modify

### Backend

| File | Change |
|------|--------|
| `lambdas/shared/models.py` | Add `GameOptions` and `PendingCombatConfirmation` models |
| `lambdas/session/models.py` | Add options to session schema |
| `lambdas/session/service.py` | Handle options in session CRUD |
| `lambdas/dm/prompts/context_builder.py` | Add options context section |
| `lambdas/dm/service.py` | Add hostility check, pending confirmation logic |
| `lambdas/dm/action_parser.py` | Add attack intent detection |

### Frontend

| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Add `GameOptions`, `PendingCombatConfirmation` types |
| `frontend/src/components/game/OptionsPanel.tsx` | New component |
| `frontend/src/components/game/index.ts` | Export new component |
| `frontend/src/pages/GamePage.tsx` | Add options state, keyboard shortcut 'o', gear icon |
| `frontend/src/services/session.ts` | Add `updateOptions` API call |

### API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sessions/{id}/options` | PATCH | Update session options |

---

## Acceptance Criteria

### Options UI
1. Gear icon in status bar opens options panel
2. Press `o` to toggle options panel (when not typing in input)
3. Options panel shows all three settings with current values
4. Changing an option saves immediately
5. Options persist across page refreshes (stored in session)

### Confirm Combat (Server-Side)
6. When ON + player attacks non-hostile → DM asks for confirmation
7. Player confirms → combat initiates normally
8. Player denies or changes action → no combat, new action processed
9. When OFF → combat initiates immediately regardless of hostility
10. Already in combat → no confirmation needed (active combatants are hostile)

### Gore Level
11. MILD → violence descriptions toned down
12. STANDARD → moderate gore (current behavior)
13. EXTREME → graphic violence descriptions

### Mature Content
14. FADE_TO_BLACK → romantic/sexual scenes cut away
15. SUGGESTIVE → sensual but not explicit (current behavior)
16. EXPLICIT → full adult content narrated

---

## Testing

### Unit Tests

```python
# Test attack intent detection
def test_detect_attack_intent():
    assert detect_attack_intent("I attack the guard") == True
    assert detect_attack_intent("I stab the shopkeeper") == True
    assert detect_attack_intent("I talk to the guard") == False
    assert detect_attack_intent("I look around") == False

# Test confirmation detection
def test_detect_confirmation():
    assert detect_confirmation("yes") == "confirm"
    assert detect_confirmation("no") == "cancel"
    assert detect_confirmation("I attack him") == "confirm"
    assert detect_confirmation("I leave the shop") == "new_action"

# Test options model
def test_game_options_defaults():
    opts = GameOptions()
    assert opts.confirm_combat_noncombat == True
    assert opts.gore_level == "standard"
    assert opts.mature_content == "suggestive"
```

### Manual Tests

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| 1 | Confirm ON, attack innocent | Toggle confirm ON → attack shopkeeper | DM asks "are you sure?" |
| 2 | Confirm YES | After #1 → say "yes" | Combat initiates |
| 3 | Confirm NO | After #1 → say "no" | No combat, can take other action |
| 4 | Confirm OFF | Toggle confirm OFF → attack shopkeeper | Combat initiates immediately |
| 5 | Gore MILD | Set gore to Mild → kill enemy | Descriptions toned down |
| 6 | Gore EXTREME | Set gore to Extreme → kill enemy | Graphic descriptions |
| 7 | Mature FADE | Set mature to Fade → romance scene | Scene cuts away |
| 8 | Mature EXPLICIT | Set mature to Explicit → romance scene | Full narration |
| 9 | Options persist | Change options → refresh page | Options preserved |
| 10 | Keyboard shortcut | Press 'o' (not in input) | Options panel toggles |

---

## Cost Impact

### Hostility Classification Call
- Only triggered when: `confirm_combat=ON` + attack detected + not in combat
- Estimated frequency: 5-10 per session (players don't attack non-hostiles often)
- Token cost per call: ~100 input + ~10 output = 110 tokens
- At worst case 10 calls/session, 100 sessions/day: 110K tokens/day
- Mistral Small cost: ~$0.22/day additional = **~$6.60/month worst case**

In practice, much lower because most attacks are against hostile enemies.

---

## Future Options (not in this init)

- Auto-loot bodies
- Show dice rolls in narrative
- DM verbosity level
- Fast travel enabled
- Difficulty modifier
- Permadeath toggle

---

## Notes

- Options are per-session, not per-user (different campaigns might want different settings)
- Default values chosen for balanced experience
- Gore/mature are prompt-only changes (straightforward)
- Combat confirmation requires server-side state management (more complex)
- Hostility classification is imperfect but errs on side of confirmation (better UX)
