"""BECMI D&D rules for character generation.

Implements character creation rules from the 1983 D&D Basic/Expert/Companion/Master set.
"""

from enum import Enum


class CharacterClass(str, Enum):
    """Available character classes for BECMI D&D."""

    FIGHTER = "fighter"
    THIEF = "thief"
    MAGIC_USER = "magic_user"
    CLERIC = "cleric"


# Hit dice by class (die size for HP rolls)
HIT_DICE: dict[CharacterClass, int] = {
    CharacterClass.FIGHTER: 8,  # 1d8
    CharacterClass.CLERIC: 6,  # 1d6
    CharacterClass.THIEF: 4,  # 1d4
    CharacterClass.MAGIC_USER: 4,  # 1d4
}


# Starting abilities by class
STARTING_ABILITIES: dict[CharacterClass, list[str]] = {
    CharacterClass.FIGHTER: ["Attack", "Parry"],
    CharacterClass.THIEF: ["Attack", "Backstab", "Pick Locks", "Hide in Shadows"],
    CharacterClass.MAGIC_USER: ["Attack", "Cast Spell"],
    CharacterClass.CLERIC: ["Attack", "Turn Undead"],
}


def get_hit_dice(character_class: CharacterClass) -> int:
    """Return hit die size for a class.

    Args:
        character_class: The character class

    Returns:
        Die size (4, 6, or 8)
    """
    return HIT_DICE[character_class]


def get_starting_abilities(character_class: CharacterClass) -> list[str]:
    """Return starting abilities for a class.

    Args:
        character_class: The character class

    Returns:
        List of ability names (a copy, safe to modify)
    """
    return STARTING_ABILITIES[character_class].copy()


def roll_starting_hp(hit_die: int, con_modifier: int) -> int:
    """Roll starting HP: 1d(hit_die) + CON modifier, minimum 1.

    Args:
        hit_die: Die size to roll (4, 6, or 8)
        con_modifier: Constitution modifier (-3 to +3)

    Returns:
        Starting HP (minimum 1)
    """
    from shared.utils import roll_dice

    rolls = roll_dice(1, hit_die)
    roll = rolls[0] if rolls else hit_die  # Fallback to max if empty
    return max(1, roll + con_modifier)


def roll_starting_gold() -> int:
    """Roll starting gold: 3d6 x 10.

    Returns:
        Starting gold pieces (30-180)
    """
    from shared.utils import roll_dice

    rolls = roll_dice(3, 6)
    return sum(rolls) * 10
