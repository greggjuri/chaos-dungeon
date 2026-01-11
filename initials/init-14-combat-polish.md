# init-14-combat-polish

## Overview

Polish the turn-based combat system implemented in init-12. Address narrator issues, prompt artifacts, and minor UX improvements discovered during testing.

## Dependencies

- init-12-turn-based-combat (COMPLETE)

## Concrete Example from Testing

Player "El Dorko" attacked a goblin. Dice results:
- El Dorko: d20(4) = MISS
- Goblin: d20(18)+1 = 19 HIT
- Goblin damage: d6(4) = 4 (lethal)

AI narrated:
> "El Dorko's sword swishes through the air, barely grazing the cackling goblin... El Dorko's eyes widen in shock as the goblin's blade sinks into his chest... His lifeless body collapses to the ground... **The Mighty Warrior plunges his sword deep into the goblin's heart**, a victorious roar escaping his lips. The goblin's eyes bulge in terror... blood pooling around its corpse. N"

Problems:
1. "The Mighty Warrior" doesn't exist - hallucinated character
2. Goblin is narrated as dying when El Dorko died (contradicts mechanical outcome)
3. Narrative cut off mid-word ("corpse. N")
4. `Narrative:` and `State Changes:` headers leaked in previous message

## Issues to Fix

### 1. Narrator Prompt Artifacts
Still seeing `[DM]:`, `Narrative:`, `State Changes:` in output. Add to cleaning patterns.

### 2. Narrator Hallucination
AI sometimes adds extra characters/actions not in the actual combat (e.g., "The warlock hurls a shadowy bolt at the rogue" when neither exists). Tighten narrator prompt to ONLY describe the provided combat results.

### 3. Narrative Truncation
Narratives sometimes cut off mid-sentence ("who narrowly avoid"). Either:
- Increase max_tokens for narrator
- Or add sentence completion check

### 4. DM Solo Combat
When player initiates combat via free text, DM sometimes narrates multiple rounds without waiting for player input. Reinforce that combat MUST use turn-based UI once initiated.

### 5. Enemy Name Disambiguation
When multiple enemies of same type (e.g., 3 "Fighter"), the pills show "Fighter", "Fighter", "Fighter". Should show "Fighter 1", "Fighter 2", "Fighter 3" for clarity.

### 6. Free Text Target Parsing
Player typed "Attack Fighter" but with 3 fighters, which one gets attacked? Should either:
- Attack first living fighter (current behavior?)
- Or prompt player to specify which one

## Out of Scope

- Spellcasting system (separate init)
- Inventory/item usage modal
- Status effects
- Multiple attacks per round for high-level fighters

## Acceptance Criteria

- [ ] No prompt artifacts in player-visible text
- [ ] Narrator only describes provided combat outcomes
- [ ] Narratives complete (no mid-sentence cutoff)
- [ ] Combat always uses turn-based UI, no DM solo resolution
- [ ] Multiple same-type enemies have numbered names
- [ ] Free text targeting works predictably

## Cost Impact

Minimal - may need slightly more tokens for narrator if we increase max_tokens.

## Notes

This is polish work. The core turn-based system from init-12 is functional. These fixes improve immersion and UX consistency.
