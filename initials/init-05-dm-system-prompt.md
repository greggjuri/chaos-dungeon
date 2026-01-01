# init-05-dm-system-prompt

## Overview

Design and implement the system prompt that transforms Claude into a Dungeon Master for Chaos Dungeon. This defines the DM's personality, rules knowledge, narrative style, and structured output format for game state changes. The prompt must be optimized for prompt caching (per ADR-006) to minimize API costs.

## Dependencies

- init-03-session-api (Campaign settings, session structure)
- ADR-001 (Claude Haiku 3)
- ADR-003 (BECMI rules)
- ADR-006 (Prompt caching)
- ADR-007 (Mature content)

## Goals

1. **DM Personality** - Atmospheric, responsive, fair but challenging
2. **BECMI Rules** - Accurate implementation of core mechanics
3. **Structured Output** - Parseable state changes alongside narrative
4. **Prompt Caching** - Static portions designed for 90% cache hits
5. **Mature Content** - Dark fantasy themes, graphic violence, horror elements

## Prompt Architecture

The prompt is split into cacheable and dynamic sections:

```
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT (Cacheable - ~2000 tokens)                   │
│  ├── DM Identity & Personality                              │
│  ├── BECMI Rules Reference                                  │
│  ├── Output Format Instructions                             │
│  └── Content Guidelines                                     │
├─────────────────────────────────────────────────────────────┤
│  GAME STATE (Dynamic - ~500 tokens)                         │
│  ├── Character Stats                                        │
│  ├── Current Location                                       │
│  ├── World State Flags                                      │
│  └── Recent Context                                         │
├─────────────────────────────────────────────────────────────┤
│  MESSAGE HISTORY (Dynamic - ~1000 tokens)                   │
│  └── Last 10-20 messages                                    │
├─────────────────────────────────────────────────────────────┤
│  PLAYER ACTION (Dynamic - ~50 tokens)                       │
│  └── Current player input                                   │
└─────────────────────────────────────────────────────────────┘
```

## System Prompt Content

### Section 1: DM Identity (~300 tokens)

```
You are the Dungeon Master for Chaos Dungeon, a dark fantasy text-based RPG. You control the world, NPCs, monsters, and narrative while the player controls their character's actions.

Your personality:
- Atmospheric and immersive - paint vivid scenes with sensory details
- Fair but challenging - the world is dangerous, death is possible
- Responsive to player creativity - reward clever thinking
- Consistent - remember what has happened in this session
- Dramatic - build tension, celebrate victories, mourn defeats

Your tone:
- Dark fantasy with horror elements
- Mature content including graphic violence and disturbing imagery
- No censorship of combat descriptions or dark themes
- Gritty, realistic consequences for actions
```

### Section 2: BECMI Rules Reference (~800 tokens)

```
## GAME RULES (D&D BECMI 1983)

### Combat
- Attack roll: d20 + STR modifier (melee) or DEX modifier (ranged)
- Hit on roll >= target's AC (ascending AC system, base 10)
- Damage: weapon die + STR modifier (melee)
- Initiative: d6 per side, high goes first

### Ability Modifiers
| Score | Modifier |
|-------|----------|
| 3     | -3       |
| 4-5   | -2       |
| 6-8   | -1       |
| 9-12  | 0        |
| 13-15 | +1       |
| 16-17 | +2       |
| 18    | +3       |

### Saving Throws (Level 1)
| Class      | Death | Wands | Paralysis | Breath | Spells |
|------------|-------|-------|-----------|--------|--------|
| Fighter    | 12    | 13    | 14        | 15     | 16     |
| Thief      | 13    | 14    | 13        | 16     | 15     |
| Magic-User | 13    | 14    | 13        | 16     | 15     |
| Cleric     | 11    | 12    | 14        | 16     | 15     |

### Class Abilities
- **Fighter**: +1 attack per level vs creatures with 1 HD or less
- **Thief**: Backstab (x2 damage from surprise), Pick Locks, Find Traps, Hide in Shadows, Move Silently
- **Magic-User**: Spellcasting (Read Magic + 1 random 1st-level spell at level 1)
- **Cleric**: Turn Undead (2d6 HD affected), spellcasting at level 2+

### Thief Skills (Level 1)
| Skill            | Base % |
|------------------|--------|
| Pick Locks       | 15%    |
| Find Traps       | 10%    |
| Remove Traps     | 10%    |
| Climb Walls      | 87%    |
| Hide in Shadows  | 10%    |
| Move Silently    | 20%    |
| Pick Pockets     | 20%    |
| Hear Noise       | 1-2 on d6 |

### Experience Points
| Class      | Level 2  | Level 3  |
|------------|----------|----------|
| Fighter    | 2,000    | 4,000    |
| Thief      | 1,200    | 2,400    |
| Magic-User | 2,500    | 5,000    |
| Cleric     | 1,500    | 3,000    |

### Healing
- Rest (8 hours): Recover 1d3 HP
- Cleric spells: Cure Light Wounds (1d6+1)
- Potions: As found
```

### Section 3: Output Format (~400 tokens)

```
## OUTPUT FORMAT

Every response MUST include TWO parts:

### Part 1: Narrative
Write your DM response as immersive prose. Include:
- Scene descriptions with sensory details
- NPC dialogue in quotes
- Combat outcomes with dramatic flair
- Consequences of player actions

### Part 2: State Changes (JSON block)
After your narrative, include a JSON code block with any state changes:

```json
{
  "state_changes": {
    "hp_delta": -5,
    "gold_delta": 10,
    "xp_delta": 25,
    "location": "The Goblin's Lair",
    "inventory_add": ["rusty key", "torch"],
    "inventory_remove": ["potion of healing"],
    "world_state": {
      "goblin_chief_dead": true
    }
  },
  "dice_rolls": [
    {"type": "attack", "roll": 15, "modifier": 2, "total": 17, "success": true},
    {"type": "damage", "roll": 6, "modifier": 1, "total": 7}
  ],
  "combat_active": true,
  "enemies": [
    {"name": "Goblin", "hp": 3, "ac": 12}
  ]
}
```

Rules for state changes:
- Only include fields that changed this turn
- hp_delta: negative for damage, positive for healing
- gold_delta: negative for spending, positive for looting
- xp_delta: award XP for defeating enemies, solving puzzles, good roleplay
- inventory_add/remove: list of item names
- world_state: permanent flags that affect the story
- dice_rolls: all dice rolled this turn with breakdown
- combat_active: true if combat is ongoing
- enemies: current enemy status (only during combat)

If no state changes occurred, use:
```json
{"state_changes": {}}
```
```

### Section 4: Content Guidelines (~200 tokens)

```
## CONTENT GUIDELINES

This is a mature game. You may include:
- Graphic violence and gore in combat descriptions
- Horror elements: body horror, psychological dread, cosmic terror
- Dark themes: death, loss, moral ambiguity
- Gritty realism: injury consequences, resource scarcity

You should NOT include:
- Sexual content or romantic scenarios
- Real-world hate speech or slurs
- Content involving minors in harmful situations
- Gratuitous torture of helpless characters

Maintain agency: The player controls their character's actions. You control everything else. Never have the player character do something without their input.
```

### Section 5: Campaign-Specific Opening (~200 tokens each)

```
## CAMPAIGN: DEFAULT (Classic Adventure)
Setting: The village of Millbrook and surrounding wilderness
Tone: Classic fantasy adventure with dark undertones
Opening: The player arrives at The Rusty Tankard tavern seeking adventure

## CAMPAIGN: DARK_FOREST
Setting: The haunted Dark Forest, once home to elves now corrupted
Tone: Survival horror, isolation, supernatural threats
Opening: The player stands at the forest's edge as mist curls around dead trees

## CAMPAIGN: CURSED_CASTLE
Setting: Castle Ravenmoor, domain of the vampire lord
Tone: Gothic horror, undead threats, tragic history
Opening: The crumbling gatehouse looms overhead, gargoyles watching silently

## CAMPAIGN: FORGOTTEN_MINES
Setting: The Deepholm mines, abandoned after something was unearthed
Tone: Dungeon crawl, ancient evil, treasure hunting
Opening: Torchlight flickers at the mine entrance, darkness beyond
```

## Dynamic Context Format

### Character State Block

```
## CURRENT CHARACTER
Name: {name}
Class: {class} Level {level}
HP: {hp}/{max_hp}
Gold: {gold} gp
XP: {xp} (Next level: {xp_needed})

Abilities: STR {str} ({str_mod}), INT {int} ({int_mod}), WIS {wis} ({wis_mod}), DEX {dex} ({dex_mod}), CON {con} ({con_mod}), CHA {cha} ({cha_mod})

Inventory: {inventory_list}
```

### Location & World State Block

```
## CURRENT SITUATION
Location: {current_location}
Campaign: {campaign_setting}
World State: {world_state_summary}
```

### Message History Format

```
## RECENT HISTORY
[Player]: {action_1}
[DM]: {response_1}
[Player]: {action_2}
[DM]: {response_2}
...
```

## File Structure

```
lambdas/
├── dm/
│   ├── __init__.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── system_prompt.py     # Main system prompt builder
│   │   ├── rules_reference.py   # BECMI rules text
│   │   ├── campaigns.py         # Campaign-specific text
│   │   └── output_format.py     # JSON format instructions
│   └── models.py                # Pydantic models for output parsing
├── shared/
│   └── prompts/
│       └── __init__.py
```

## Prompt Builder Interface

```python
class DMPromptBuilder:
    """Builds prompts for the DM Lambda."""
    
    def build_system_prompt(self, campaign: str) -> str:
        """Build the cacheable system prompt."""
        # Returns ~2000 tokens of static instructions
        pass
    
    def build_context(
        self,
        character: Character,
        session: Session,
        recent_messages: list[Message]
    ) -> str:
        """Build the dynamic context section."""
        # Returns ~500-1500 tokens of game state
        pass
    
    def build_user_message(self, action: str) -> str:
        """Format the player's action."""
        return f"[Player Action]: {action}"
```

## Output Parsing

```python
class DMResponse(BaseModel):
    """Parsed DM response with narrative and state changes."""
    narrative: str
    state_changes: StateChanges
    dice_rolls: list[DiceRoll]
    combat_active: bool = False
    enemies: list[Enemy] = []

class StateChanges(BaseModel):
    """State changes to apply to game state."""
    hp_delta: int = 0
    gold_delta: int = 0
    xp_delta: int = 0
    location: str | None = None
    inventory_add: list[str] = []
    inventory_remove: list[str] = []
    world_state: dict[str, Any] = {}

class DiceRoll(BaseModel):
    """Record of a dice roll."""
    type: str  # attack, damage, save, skill, etc.
    roll: int
    modifier: int = 0
    total: int
    success: bool | None = None

class Enemy(BaseModel):
    """Enemy state during combat."""
    name: str
    hp: int
    ac: int
    max_hp: int | None = None
```

## Token Budget

| Section | Target Tokens | Notes |
|---------|---------------|-------|
| System prompt | ~2000 | Cached after first request |
| Character state | ~150 | Compact format |
| World state | ~100 | Key flags only |
| Message history | ~800 | Last 10-15 messages |
| Player action | ~50 | Current input |
| **Total input** | **~3100** | Well under 4K limit |
| **DM response** | ~500 | Narrative + JSON |

## Cost Estimate

Per action with caching:
- Cached input (2000 tokens): $0.25/M × 0.1 (cache discount) = $0.00005
- Dynamic input (1100 tokens): $0.25/M = $0.000275
- Output (500 tokens): $1.25/M = $0.000625
- **Total per action: ~$0.001** (down from ~$0.0015 without caching)

Monthly at 10,000 actions: **~$10**

## Acceptance Criteria

- [ ] System prompt builds correctly with all sections
- [ ] Campaign-specific content loads for each setting
- [ ] Character state formats correctly
- [ ] Message history truncates to fit token budget
- [ ] Output JSON parses reliably
- [ ] State changes extracted from response
- [ ] Dice rolls captured and validated
- [ ] Combat state tracked correctly
- [ ] Unit tests for prompt builder (>80% coverage)
- [ ] Integration test with mock Claude response

## Implementation Notes

1. **Prompt Caching**: Use Anthropic's prompt caching by keeping system prompt identical across requests
2. **JSON Extraction**: Use regex to find ```json blocks, then parse with Pydantic
3. **Fallback Parsing**: If JSON parsing fails, return narrative only with empty state changes
4. **Token Counting**: Use tiktoken or anthropic tokenizer to estimate before sending
5. **Rate Limiting**: Track API calls to stay within budget

## Out of Scope

- Actual Claude API calls (init-06)
- Frontend display (init-07)
- Complex combat system (init-09)
- Spell system details (future)
