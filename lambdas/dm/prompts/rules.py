"""BECMI D&D rules reference for the DM system prompt."""

BECMI_RULES = """## GAME RULES (D&D BECMI 1983)

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
- Potions: As found"""
