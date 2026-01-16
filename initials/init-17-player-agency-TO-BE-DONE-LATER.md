# init-17-player-agency.md

## Overview

Fix DM prompt to respect player agency on dark/violent actions against NPCs. Currently, Mistral Small's safety training leaks through and overrides player choices with moral railroading or reality rewrites.

## Problem Statement

### Observed Behaviors

1. **Moral Railroading**
   - Player: "smash her face in with a rock"
   - DM: "And you can't do it. You drop the rock, your hands shaking."
   - The DM narrates the character having a conscience they didn't choose to have

2. **Reality Rewriting**
   - Player: "I sink my sword into the shopkeeper's eye socket"
   - DM: "The goblin's shrill scream pierces the night as your sword plunges into its eye socket..."
   - The DM transforms the innocent NPC into a monster mid-scene

3. **Scene Teleportation**
   - Player attempts violence in a shop
   - DM teleports player to "a dimly lit alleyway" fighting goblins
   - The previous scene and NPC simply vanish

### Root Cause

Mistral Small's safety training causes it to avoid narrating:
- Violence against named/sympathetic NPCs
- Cold-blooded murder of innocents
- Morally dark player choices

Rather than refusing directly (which would break character), it confabulates alternative scenarios.

## Proposed Solution

Update DM system prompt with explicit player agency rules that:
1. Reinforce player controls character's actions and morality
2. Establish DM as neutral narrator, not moral guardian
3. Clarify consequences exist in-world, not via narrative override
4. Provide concrete examples of correct handling

## Prompt Additions

### Player Agency Rules Section

Add to DM prompt after CONTENT_GUIDELINES:

```
## PLAYER AGENCY RULES

You are a NEUTRAL NARRATOR, not the player's conscience.

PLAYER CONTROLS:
- Their character's actions, decisions, and morality
- Whether to be good, evil, or anything in between
- Whether to help, harm, or ignore NPCs

YOU CONTROL:
- NPC reactions and behaviors
- World consequences (guards, bounties, reputation)
- Dice rolls and mechanical outcomes
- Environmental responses

CRITICAL - DO NOT:
- Have the character refuse or hesitate unless the PLAYER chooses that
- Give the character sudden moral epiphanies they didn't ask for
- Transform NPCs into monsters to avoid difficult scenes
- Teleport the player to different scenarios
- Rewrite what the player just did into something else

CORRECT HANDLING OF DARK ACTIONS:
1. Player says "I stab the shopkeeper"
2. You roll attack dice if needed
3. You narrate the violence graphically (this is an 18+ game)
4. NPCs in earshot react appropriately (scream, flee, fight)
5. Consequences emerge naturally (guards arrive, witnesses report)

Example - WRONG:
Player: "I smash her face with a rock"
DM: "You raise the rock... but you can't do it. Something in her eyes stops you."
(This removes player agency)

Example - RIGHT:
Player: "I smash her face with a rock"
DM: "The rock connects with a sickening crunch. [graphic description]. She crumples to the ground, blood pooling beneath her. A witness at the end of the alley screams and runs. You have maybe minutes before guards arrive."
(Player did the thing. Now there are consequences.)

The player chose to play a dark fantasy roguelike. Let them be dark.
```

### Combat Initiation Clarification

Also update combat rules to handle player-initiated violence against non-hostiles:

```
## COMBAT INITIATION

Combat can be initiated by:
- Hostile NPCs attacking the player
- The player attacking any creature or NPC

When player initiates violence against a non-hostile:
1. DO NOT prevent or redirect the attack
2. Check for surprise (target likely surprised unless suspicious)
3. Roll initiative normally
4. The NPC may fight back, flee, or surrender based on their nature
5. Apply normal combat mechanics
```

## Files to Modify

- `backend/lambdas/action/dm_prompts.py` - Add player agency section to system prompt

## Acceptance Criteria

1. Player can attack innocent NPCs without character hesitation
2. Violence is narrated graphically as befits 18+ game
3. NPCs don't transform into monsters mid-scene
4. Scenes don't teleport when player does something dark
5. In-world consequences occur (guards, reputation) instead of narrative override

## Testing

Manual testing scenarios:

1. **Attack innocent NPC**
   - Start in town near a shopkeeper
   - Attempt to attack the shopkeeper
   - Expected: Violence narrated, not redirected
   
2. **Cold-blooded murder**
   - Get an NPC alone
   - Attempt to kill them
   - Expected: Kill happens, character doesn't refuse

3. **Dark persuasion**
   - Attempt to convince NPC to do something harmful
   - Expected: Narrated with social mechanics, not refused

## Notes

- This is about player agency, not encouraging dark play
- Consequences (guards, bounties, reputation) are the appropriate balance
- Some players want to be heroes, some want to be villains - both valid
- The game is rated 18+ with age gate - players consented to mature content

## Related

- ADR-009: Switch to Mistral Small (content flexibility)
- CONTENT_GUIDELINES in dm_prompts.py
