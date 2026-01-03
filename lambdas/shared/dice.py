"""Dice rolling utilities with standard notation support.

Provides functions for rolling dice using D&D-style notation (e.g., "2d6+3").
Used for combat resolution, ability scores, and other game mechanics.
"""

import random
import re


def roll(notation: str) -> tuple[int, list[int]]:
    """Roll dice using standard notation.

    Supports notation like "1d20", "2d6+3", "1d8-1", "3d6".

    Args:
        notation: Dice notation string (e.g., "2d6+3")

    Returns:
        Tuple of (total, individual_rolls)
        - total: Sum of all rolls plus modifier
        - individual_rolls: List of each die result (before modifier)

    Raises:
        ValueError: If notation is invalid

    Examples:
        >>> roll("1d20")  # Returns something like (15, [15])
        >>> roll("2d6+3")  # Returns something like (11, [4, 4]) where 4+4+3=11
        >>> roll("1d8-1")  # Returns something like (5, [6]) where 6-1=5
    """
    if not notation or not isinstance(notation, str):
        raise ValueError(f"Invalid dice notation: {notation}")

    # Normalize: lowercase and remove spaces
    normalized = notation.lower().replace(" ", "")

    # Pattern: NdS or NdS+M or NdS-M
    pattern = r"^(\d+)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, normalized)

    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier_str = match.group(3)
    modifier = int(modifier_str) if modifier_str else 0

    if num_dice < 1:
        raise ValueError("Invalid dice notation: must roll at least 1 die")
    if die_size < 1:
        raise ValueError("Invalid dice notation: die must have at least 1 side")

    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier

    return total, rolls


def roll_attack(attack_bonus: int = 0) -> tuple[int, int]:
    """Roll a d20 attack roll.

    Args:
        attack_bonus: Modifier to add to the roll

    Returns:
        Tuple of (total, natural_roll)
        - total: Natural roll plus bonus
        - natural_roll: The unmodified d20 result
    """
    natural = random.randint(1, 20)
    return natural + attack_bonus, natural


def roll_initiative() -> int:
    """Roll d6 for BECMI-style initiative.

    In BECMI D&D, initiative is rolled on a d6, with higher going first.

    Returns:
        Initiative roll (1-6)
    """
    return random.randint(1, 6)


def roll_save(save_target: int, modifier: int = 0) -> tuple[bool, int]:
    """Roll a saving throw.

    Args:
        save_target: Target number to meet or beat
        modifier: Bonus/penalty to the roll

    Returns:
        Tuple of (success, total_roll)
    """
    natural = random.randint(1, 20)
    total = natural + modifier
    return total >= save_target, total
