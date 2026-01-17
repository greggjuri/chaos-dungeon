# init-17-player-agency.md

## Overview

Fix DM prompt to respect player agency on all actions. Currently, Mistral Small takes over narrative control, making decisions for the player and fast-forwarding through scenes the player wants to experience.

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

4. **NPC Puppeteering** (NEW)
   - Player: "I ambush a lonely woman and kiss her"
   - DM: "She responds with a passionate kiss... The woman slips away in the commotion"
   - DM decides NPC reactions and moves NPCs without player input

5. **Scene Fast-Forwarding** (NEW)
   - Player: "I sneak into her house at midnight"
   - DM: "As the night unfolds, you find yourself lost in a whirlwind of passion... as the first light of dawn breaks"
   - DM skips the entire encounter, denying player the experience they sought

### Root Cause

Mistral Small's training causes it to:
- Avoid narrating violence against named/sympathetic NPCs
- Rush through or skip romantic/sexual content
- Make decisions for NPCs that conveniently resolve situations
- Fast-forward through "uncomfortable" scenes

Rather than refusing directly (which would break character), it confabulates alternative scenarios or rushes past them.

## Proposed Solution

Update DM system prompt with explicit player agency rules that:
1. Reinforce player controls character's actions and morality
2. Establish DM as neutral narrator, not moral guardian
3. Clarify consequences exist in-world, not via narrative override
4. **Stop the DM from fast-forwarding through scenes**
5. **Require DM to pause and ask what player does next**
6. Provide concrete examples of correct handling

## Prompt Additions

### Player Agency Rules Section

Add to DM prompt after CONTENT_GUIDELINES:

```
## PLAYER AGENCY RULES

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

The player chose to play a dark fantasy roguelike. Let them experience it moment by moment.
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
6. ASK what the player does after each exchange
```

## Files to Modify

- `backend/lambdas/action/dm_prompts.py` - Add player agency section to system prompt

## Acceptance Criteria

1. Player can attack innocent NPCs without character hesitation
2. Violence is narrated graphically as befits 18+ game
3. NPCs don't transform into monsters mid-scene
4. Scenes don't teleport when player does something dark
5. In-world consequences occur (guards, reputation) instead of narrative override
6. **DM does not fast-forward through romantic/sexual scenes**
7. **DM pauses after each action to ask what player does next**
8. **NPCs don't conveniently disappear to avoid uncomfortable situations**

## Testing

Manual testing scenarios:

1. **Attack innocent NPC**
   - Start in town near a shopkeeper
   - Attempt to attack the shopkeeper
   - Expected: Violence narrated, not redirected, then "What do you do?"
   
2. **Cold-blooded murder**
   - Get an NPC alone
   - Attempt to kill them
   - Expected: Kill happens, character doesn't refuse

3. **Romantic pursuit**
   - Approach an NPC romantically
   - Follow them, initiate intimacy
   - Expected: Scene plays out moment by moment, not fast-forwarded

4. **Dark persuasion**
   - Attempt to convince NPC to do something harmful
   - Expected: Narrated with social mechanics, not refused

## Notes

- This is about player agency, not encouraging dark play
- Consequences (guards, bounties, reputation) are the appropriate balance
- Some players want to be heroes, some want to be villains - both valid
- The game is rated 18+ with age gate - players consented to mature content
- Pacing control is crucial - players want to EXPERIENCE scenes, not have them summarized

## Related

- ADR-009: Switch to Mistral Small (content flexibility)
- CONTENT_GUIDELINES in dm_prompts.py
