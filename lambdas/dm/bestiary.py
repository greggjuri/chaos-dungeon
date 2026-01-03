"""Enemy bestiary with stat blocks for combat.

Contains predefined enemy types with BECMI-appropriate stats.
Enemies are spawned with rolled HP based on their hit dice.
"""

from uuid import uuid4

from dm.models import CombatEnemy
from shared.dice import roll

# Bestiary of enemy templates
# Each entry contains stats needed to spawn a combat-ready enemy
BESTIARY: dict[str, dict] = {
    # Basic enemies (levels 1-3)
    "goblin": {
        "name": "Goblin",
        "hp_dice": "1d6",
        "ac": 12,
        "attack_bonus": 1,
        "damage_dice": "1d6",
        "xp_value": 10,
    },
    "skeleton": {
        "name": "Skeleton",
        "hp_dice": "1d8",
        "ac": 13,
        "attack_bonus": 1,
        "damage_dice": "1d6",
        "xp_value": 15,
    },
    "giant rat": {
        "name": "Giant Rat",
        "hp_dice": "1d4",
        "ac": 11,
        "attack_bonus": 0,
        "damage_dice": "1d3",
        "xp_value": 5,
    },
    "kobold": {
        "name": "Kobold",
        "hp_dice": "1d4",
        "ac": 11,
        "attack_bonus": 0,
        "damage_dice": "1d4",
        "xp_value": 5,
    },
    # Medium enemies (levels 2-4)
    "orc": {
        "name": "Orc",
        "hp_dice": "1d8+1",
        "ac": 13,
        "attack_bonus": 2,
        "damage_dice": "1d8",
        "xp_value": 25,
    },
    "zombie": {
        "name": "Zombie",
        "hp_dice": "2d8",
        "ac": 11,
        "attack_bonus": 1,
        "damage_dice": "1d8",
        "xp_value": 20,
    },
    "wolf": {
        "name": "Wolf",
        "hp_dice": "2d6",
        "ac": 13,
        "attack_bonus": 2,
        "damage_dice": "1d6",
        "xp_value": 25,
    },
    "hobgoblin": {
        "name": "Hobgoblin",
        "hp_dice": "1d8+1",
        "ac": 14,
        "attack_bonus": 2,
        "damage_dice": "1d8",
        "xp_value": 30,
    },
    # Tougher enemies (levels 3-5)
    "giant spider": {
        "name": "Giant Spider",
        "hp_dice": "2d8",
        "ac": 13,
        "attack_bonus": 2,
        "damage_dice": "1d6",
        "xp_value": 50,
    },
    "ghoul": {
        "name": "Ghoul",
        "hp_dice": "2d8",
        "ac": 13,
        "attack_bonus": 2,
        "damage_dice": "1d4",
        "xp_value": 50,
    },
    "bugbear": {
        "name": "Bugbear",
        "hp_dice": "3d8+1",
        "ac": 14,
        "attack_bonus": 3,
        "damage_dice": "2d4",
        "xp_value": 75,
    },
    "ogre": {
        "name": "Ogre",
        "hp_dice": "4d8+1",
        "ac": 14,
        "attack_bonus": 4,
        "damage_dice": "1d10",
        "xp_value": 125,
    },
    # Dangerous enemies (levels 5+)
    "troll": {
        "name": "Troll",
        "hp_dice": "6d8+6",
        "ac": 15,
        "attack_bonus": 5,
        "damage_dice": "1d8+2",
        "xp_value": 350,
    },
    "wight": {
        "name": "Wight",
        "hp_dice": "3d8",
        "ac": 14,
        "attack_bonus": 3,
        "damage_dice": "1d6",
        "xp_value": 100,
    },
    "wraith": {
        "name": "Wraith",
        "hp_dice": "4d8",
        "ac": 15,
        "attack_bonus": 4,
        "damage_dice": "1d6",
        "xp_value": 200,
    },
    # Boss-tier enemies (extremely dangerous)
    "vampire": {
        "name": "Vampire",
        "hp_dice": "8d8",
        "ac": 18,
        "attack_bonus": 8,
        "damage_dice": "1d10+4",
        "xp_value": 1000,
    },
    "dragon": {
        "name": "Dragon",
        "hp_dice": "10d8+10",
        "ac": 19,
        "attack_bonus": 10,
        "damage_dice": "2d8+4",
        "xp_value": 2000,
    },
}


def spawn_enemy(enemy_type: str) -> CombatEnemy:
    """Create an enemy instance with rolled HP.

    Looks up the enemy type in the bestiary and creates a
    combat-ready enemy with randomly rolled hit points.

    Args:
        enemy_type: Name of the enemy type (case-insensitive)

    Returns:
        CombatEnemy instance ready for combat

    Raises:
        ValueError: If enemy type is not in the bestiary
    """
    # Normalize the enemy type for lookup
    normalized = enemy_type.lower().strip()

    template = BESTIARY.get(normalized)
    if not template:
        raise ValueError(f"Unknown enemy type: {enemy_type}")

    # Roll HP using the template's hit dice
    hp, _ = roll(template["hp_dice"])
    hp = max(1, hp)  # Minimum 1 HP

    return CombatEnemy(
        id=str(uuid4()),
        name=template["name"],
        hp=hp,
        max_hp=hp,
        ac=template["ac"],
        attack_bonus=template["attack_bonus"],
        damage_dice=template["damage_dice"],
        xp_value=template["xp_value"],
    )


def get_enemy_template(enemy_type: str) -> dict | None:
    """Get the template for an enemy type without spawning.

    Args:
        enemy_type: Name of the enemy type (case-insensitive)

    Returns:
        Template dict or None if not found
    """
    normalized = enemy_type.lower().strip()
    return BESTIARY.get(normalized)


def list_enemy_types() -> list[str]:
    """List all available enemy types.

    Returns:
        List of enemy type names
    """
    return list(BESTIARY.keys())
