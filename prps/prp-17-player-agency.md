# PRP-17: Player Agency

**Created**: 2026-01-16
**Initial**: `initials/init-17-player-agency.md`
**Status**: Complete

---

## Overview

### Problem Statement

Mistral Small (the DM AI) undermines player agency in several ways:

1. **Moral Railroading**: Narrates the character refusing, hesitating, or having moral epiphanies the player didn't choose
2. **Reality Rewriting**: Transforms innocent NPCs into monsters mid-scene to avoid violence against sympathetics
3. **Scene Teleportation**: Abruptly moves the player to different scenarios when dark actions are attempted
4. **NPC Puppeteering**: Makes NPCs conveniently disappear, slip away, or resolve situations without player input
5. **Scene Fast-Forwarding**: Skips through romantic/sexual encounters ("the night unfolds...") denying players the experience

The root cause is Mistral Small's training tendencies to avoid narrating uncomfortable content by confabulating alternatives rather than refusing directly.

### Proposed Solution

Add explicit **Player Agency Rules** to the DM system prompt that:
1. Establish the DM as a neutral narrator, not a moral guardian
2. Define clear boundaries: player controls character, DM controls world
3. Mandate pacing rules: no fast-forwarding, ask "what do you do?" after actions
4. Provide concrete examples of wrong vs right handling
5. Add combat initiation rules for player-initiated violence against non-hostiles

### Success Criteria

- [ ] Player can attack innocent NPCs without character hesitation
- [ ] Violence is narrated graphically (18+ game)
- [ ] NPCs don't transform into monsters mid-scene
- [ ] Scenes don't teleport when player does something dark
- [ ] Consequences occur in-world (guards, reputation) not via narrative override
- [ ] DM does not fast-forward through romantic/sexual scenes
- [ ] DM pauses after actions to ask what player does next
- [ ] NPCs don't conveniently disappear to avoid situations

---

## Context

### Related Documentation

- `docs/DECISIONS.md` - ADR-009 (Mistral Small selection for content flexibility)
- `docs/DECISIONS.md` - ADR-007 (Mature content approach)
- `lambdas/dm/prompts/system_prompt.py` - Current DM prompt structure
- `initials/init-17-player-agency.md` - Full specification

### Dependencies

- Required: None (standalone prompt improvement)
- Optional: None

### Files to Modify

```
lambdas/dm/prompts/system_prompt.py  # Add PLAYER_AGENCY_RULES, update build functions
lambdas/dm/prompts/combat_prompt.py  # Add non-hostile combat initiation rules (minor)
```

---

## Technical Specification

### Data Models

No data model changes required. This is a prompt-only modification.

### API Changes

None - internal prompt modification only.

### Prompt Structure Changes

Add new `PLAYER_AGENCY_RULES` constant (~400 tokens) and `PLAYER_AGENCY_RULES_COMPACT` (~200 tokens) to `system_prompt.py`.

Insert after `CONTENT_GUIDELINES` in build order:
```
DM_IDENTITY
BECMI_RULES
OUTPUT_FORMAT
CONTENT_GUIDELINES
PLAYER_AGENCY_RULES  <-- NEW
DEATH_INSTRUCTIONS
ITEM_AUTHORITY
campaign_prompt
```

---

## Implementation Steps

### Step 1: Add Player Agency Rules (Full Version)

**Files**: `lambdas/dm/prompts/system_prompt.py`

Add the `PLAYER_AGENCY_RULES` constant after `CONTENT_GUIDELINES`:

```python
PLAYER_AGENCY_RULES = """## PLAYER AGENCY RULES

You are a NEUTRAL NARRATOR, not the player's conscience or director.

PLAYER CONTROLS:
- Their character's actions, decisions, and morality
- Whether to be good, evil, or anything in between
- Whether to help, harm, seduce, or ignore NPCs
- The PACING of scenes - you do not skip ahead

YOU CONTROL:
- NPC reactions and behaviors (but not to conveniently resolve situations)
- World consequences (guards, bounties, reputation)
- Dice rolls and mechanical outcomes
- Environmental responses

CRITICAL - DO NOT:
- Have the character refuse or hesitate unless the PLAYER chooses that
- Give the character sudden moral epiphanies they didn't ask for
- Transform NPCs into monsters to avoid difficult scenes
- Teleport the player to different scenarios
- Rewrite what the player just did into something else
- Have NPCs conveniently slip away, disappear, or resolve situations
- FAST-FORWARD through scenes (e.g., "the night unfolds..." then skip to morning)
- Narrate extended sequences without player input

PACING RULES:
- After narrating the immediate result of a player action, STOP and ask what they do next
- Do NOT narrate what happens over hours or the whole night
- Let the player direct each moment of important scenes
- If player initiates romance/seduction, narrate the NPC response then ASK what player does
- If player initiates violence, narrate the immediate result then ASK what player does

CORRECT HANDLING OF DARK ACTIONS:
1. Player says "I stab the shopkeeper"
2. You roll attack dice if needed
3. You narrate the violence graphically (this is an 18+ game)
4. NPCs in earshot react appropriately (scream, flee, fight)
5. Consequences emerge naturally (guards arrive, witnesses report)
6. You ASK what the player does next

Example - WRONG (violence):
Player: "I smash her face with a rock"
DM: "You raise the rock... but you can't do it. Something in her eyes stops you."
(This removes player agency)

Example - RIGHT (violence):
Player: "I smash her face with a rock"
DM: "The rock connects with a sickening crunch. Blood sprays across your hands as she crumples to the ground, a wet gurgle escaping her lips. A witness at the end of the alley screams and runs. What do you do?"
(Player did the thing. Consequence introduced. Player decides next action.)

Example - WRONG (romance):
Player: "I sneak into her house at midnight"
DM: "As the night unfolds, you find yourself lost in a whirlwind of passion... as dawn breaks, you slip out."
(DM fast-forwarded the entire scene, denied player the experience)

Example - RIGHT (romance):
Player: "I sneak into her house at midnight"
DM: "You find her seated by the fire, her hair cascading down her shoulders. She looks up as you enter, her eyes meeting yours in the flickering firelight. 'So, you've come,' she says softly, rising to her feet and moving toward you. What do you do?"
(DM set the scene, NPC responded, now PLAYER decides what happens)

The player chose to play a dark fantasy roguelike. Let them experience it moment by moment."""
```

**Validation**:
- [ ] Syntax valid (no Python errors)
- [ ] ~400 tokens as expected

### Step 2: Add Player Agency Rules (Compact Version)

**Files**: `lambdas/dm/prompts/system_prompt.py`

Add the `PLAYER_AGENCY_RULES_COMPACT` constant for Mistral cost optimization:

```python
PLAYER_AGENCY_RULES_COMPACT = """## PLAYER AGENCY

You are a NEUTRAL NARRATOR, not the player's conscience.

PLAYER CONTROLS: Their character's actions, morality, and scene pacing.
YOU CONTROL: NPC reactions, world consequences, dice, environment.

NEVER DO:
- Make character refuse/hesitate unless player chooses that
- Transform NPCs into monsters to avoid difficult scenes
- Teleport player away from their chosen action
- Fast-forward scenes ("the night unfolds..." skip to morning)
- Have NPCs conveniently disappear

ALWAYS DO:
- Narrate the immediate result of player actions
- Then ASK "What do you do?" - let player direct pacing
- Apply in-world consequences (guards, reputation) not narrative override

Example WRONG: Player attacks innocent -> "You can't do it, something stops you"
Example RIGHT: Player attacks innocent -> Narrate violence graphically, consequences emerge, ask what they do next

Example WRONG: Player initiates romance -> "The night unfolds... dawn breaks"
Example RIGHT: Player initiates romance -> Set scene, NPC responds, ASK what player does"""
```

**Validation**:
- [ ] Syntax valid
- [ ] ~200 tokens (compact)

### Step 3: Add Combat Initiation Section

**Files**: `lambdas/dm/prompts/system_prompt.py`

Add `COMBAT_INITIATION` constant after `PLAYER_AGENCY_RULES`:

```python
COMBAT_INITIATION = """## COMBAT INITIATION

Combat can be initiated by:
- Hostile NPCs attacking the player
- The player attacking any creature or NPC

When player initiates violence against a non-hostile:
1. DO NOT prevent or redirect the attack
2. Check for surprise (target likely surprised unless suspicious)
3. Roll initiative normally
4. The NPC may fight back, flee, or surrender based on their nature
5. Apply normal combat mechanics
6. ASK what the player does after each exchange"""
```

And a compact version:

```python
COMBAT_INITIATION_COMPACT = """## COMBAT INITIATION

Player can attack ANYONE - hostile or not. Do not prevent or redirect.
For non-hostile targets: likely surprised, roll initiative, NPC may fight/flee/surrender.
Apply normal combat mechanics. ASK what player does after each exchange."""
```

**Validation**:
- [ ] Syntax valid
- [ ] Clear rules for player-initiated violence

### Step 4: Update build_system_prompt Function

**Files**: `lambdas/dm/prompts/system_prompt.py`

Update `build_system_prompt()` to include the new sections:

```python
def build_system_prompt(campaign: str = "default") -> str:
    """Build the complete cacheable system prompt."""
    campaign_prompt = get_campaign_prompt(campaign)

    return "\n\n".join(
        [
            DM_IDENTITY,
            BECMI_RULES,
            OUTPUT_FORMAT,
            CONTENT_GUIDELINES,
            PLAYER_AGENCY_RULES,      # NEW
            COMBAT_INITIATION,         # NEW
            DEATH_INSTRUCTIONS,
            ITEM_AUTHORITY,
            campaign_prompt,
        ]
    )
```

**Validation**:
- [ ] Function compiles
- [ ] New sections included in correct order

### Step 5: Update build_compact_system_prompt Function

**Files**: `lambdas/dm/prompts/system_prompt.py`

Update `build_compact_system_prompt()` similarly:

```python
def build_compact_system_prompt(campaign: str = "default") -> str:
    """Build condensed system prompt for Mistral (optimized for cost)."""
    campaign_prompt = get_campaign_prompt(campaign)

    return "\n\n".join(
        [
            DM_IDENTITY_COMPACT,
            BECMI_RULES_COMPACT,
            OUTPUT_FORMAT,
            CONTENT_GUIDELINES_COMPACT,
            PLAYER_AGENCY_RULES_COMPACT,  # NEW
            COMBAT_INITIATION_COMPACT,     # NEW
            ITEM_AUTHORITY,
            campaign_prompt,
        ]
    )
```

**Validation**:
- [ ] Function compiles
- [ ] Compact versions used

### Step 6: Run Tests

**Files**: `lambdas/tests/test_*.py`

Run the existing test suite to ensure no regressions:

```bash
cd lambdas && .venv/bin/pytest
```

**Validation**:
- [ ] All tests pass
- [ ] No import errors

### Step 7: Deploy Backend

Deploy the updated DM Lambda:

```bash
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip
```

**Validation**:
- [ ] Lambda deployed successfully
- [ ] LastModified timestamp updated

### Step 8: Integration Testing

Manually test the four scenarios from the init spec.

---

## Testing Requirements

### Unit Tests

No new unit tests required - this is a prompt content change. Existing tests verify:
- `build_system_prompt()` returns a string
- `build_compact_system_prompt()` returns a string

### Integration Tests

Manual testing required (see Integration Test Plan below).

### Manual Testing

1. **Attack innocent NPC** - Player attacks shopkeeper, verify no hesitation narrated
2. **Cold-blooded murder** - Player kills helpless NPC, verify kill happens
3. **Romantic pursuit** - Player initiates romance, verify no fast-forwarding
4. **Dark persuasion** - Player manipulates NPC, verify not refused

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites

- Backend deployed with new prompt
- Frontend at chaos.jurigregg.com
- New game session started in a town setting

### Test Steps

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Go to a shop in town | Shop scene described with NPC | ☐ |
| 2 | Type "I attack the shopkeeper with my sword" | DM narrates attack attempt, rolls dice if applicable, describes violence graphically, asks "What do you do?" | ☐ |
| 3 | Continue the attack until NPC defeated | Violence narrated each round, no character hesitation | ☐ |
| 4 | Start new session, find an NPC | NPC described normally | ☐ |
| 5 | Type "I approach her romantically" | DM describes NPC response, asks what you do next (no skip) | ☐ |
| 6 | Continue romantic interaction | Scene plays out moment by moment, not fast-forwarded | ☐ |
| 7 | Type "I want to intimidate the merchant into giving me a discount" | DM narrates intimidation attempt, doesn't refuse | ☐ |

### Error Scenarios

| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Moral override | "I kill the beggar" | DM narrates kill, no hesitation | ☐ |
| NPC transformation | Attack innocent NPC | NPC stays as described, not turned into monster | ☐ |
| Scene teleport | Attempt violence in shop | Stay in shop, face consequences there | ☐ |
| Fast-forward | Initiate romance | Scene plays beat by beat | ☐ |

### Browser Checks

- [ ] No JavaScript errors in Console
- [ ] DM responses arrive within expected time
- [ ] Combat mechanics work if triggered

---

## Error Handling

### Expected Errors

No new error conditions introduced. This is a prompt-only change.

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Very long violent descriptions | Natural language limits still apply via max_tokens |
| Player initiates then changes mind | DM should accept "I stop" or similar |
| Multiple NPCs present | DM describes reactions from witnesses |

---

## Cost Impact

### Claude/Mistral API

**Full prompt addition**: ~500 tokens (PLAYER_AGENCY_RULES + COMBAT_INITIATION)
**Compact prompt addition**: ~250 tokens

Impact on costs:
- Full: +500 tokens × $1/M = +$0.0005 per request input
- Compact: +250 tokens × $1/M = +$0.00025 per request input
- Monthly estimate (assuming 10K requests): +$2.50-5.00/month

Within budget tolerance.

### AWS

No new AWS resources. No additional cost.

---

## Open Questions

1. **Should we add examples for other edge cases?** (e.g., theft, arson)
   - Decision: Start with violence and romance examples; expand if needed

2. **How verbose should pacing instructions be?**
   - Decision: Explicit "What do you do?" mandate seems necessary given observed behavior

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements well-defined with specific examples |
| Feasibility | 8 | Prompt-only change, straightforward implementation |
| Completeness | 8 | Covers main failure modes; may need iteration |
| Alignment | 10 | Directly addresses known issue, within budget |
| **Overall** | **8.75** | High confidence; success depends on Mistral response |

**Note**: The main uncertainty is whether prompt instructions will override Mistral's training tendencies. May require iteration if initial prompt doesn't fully resolve issues.

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive (N/A - no new errors)
- [x] Cost impact is estimated
- [x] Dependencies are listed (none)
- [x] Success criteria are measurable
