"""Loot tables and rolling functions for Chaos Dungeon.

Implements BECMI-style loot generation from weighted tables.
Loot is rolled server-side when combat ends.
"""

import random

from aws_lambda_powertools import Logger

from shared.dice import roll as roll_dice

logger = Logger(child=True)

# =============================================================================
# LOOT TABLES - Weighted item drops by enemy/container type
# =============================================================================

LOOT_TABLES: dict[str, dict] = {
    # Basic enemies
    "goblin": {
        "gold_dice": "1d6",
        "rolls": 1,
        "items": [
            {"weight": 50, "item": None},
            {"weight": 30, "item": "dagger"},
            {"weight": 15, "item": "rations"},
            {"weight": 5, "item": "potion_healing"},
        ]
    },
    "kobold": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 60, "item": None},
            {"weight": 25, "item": "torch"},
            {"weight": 15, "item": "dagger"},
        ]
    },
    "skeleton": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 55, "item": None},
            {"weight": 25, "item": "rusty_key"},
            {"weight": 15, "item": "ancient_scroll"},
            {"weight": 5, "item": "sword"},
        ]
    },
    "giant_rat": {
        "gold_dice": "1d3",
        "rolls": 1,
        "items": [
            {"weight": 80, "item": None},
            {"weight": 20, "item": "rations"},
        ]
    },
    # Medium enemies
    "orc": {
        "gold_dice": "2d6",
        "rolls": 1,
        "items": [
            {"weight": 40, "item": None},
            {"weight": 30, "item": "sword"},
            {"weight": 20, "item": "shield"},
            {"weight": 10, "item": "potion_healing"},
        ]
    },
    "zombie": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 70, "item": None},
            {"weight": 20, "item": "rusty_key"},
            {"weight": 10, "item": "ancient_scroll"},
        ]
    },
    "hobgoblin": {
        "gold_dice": "2d6",
        "rolls": 1,
        "items": [
            {"weight": 35, "item": None},
            {"weight": 30, "item": "sword"},
            {"weight": 20, "item": "chain_mail"},
            {"weight": 15, "item": "potion_healing"},
        ]
    },
    "wolf": {
        "gold_dice": "0d0",  # No gold from animals
        "rolls": 1,
        "items": [
            {"weight": 70, "item": None},
            {"weight": 30, "item": "rations"},  # Meat
        ]
    },
    # Tougher enemies
    "giant_spider": {
        "gold_dice": "1d6",
        "rolls": 1,
        "items": [
            {"weight": 60, "item": None},
            {"weight": 25, "item": "ancient_scroll"},
            {"weight": 15, "item": "potion_healing"},
        ]
    },
    "ghoul": {
        "gold_dice": "2d6",
        "rolls": 1,
        "items": [
            {"weight": 50, "item": None},
            {"weight": 25, "item": "rusty_key"},
            {"weight": 15, "item": "golden_key"},
            {"weight": 10, "item": "potion_healing"},
        ]
    },
    "bugbear": {
        "gold_dice": "3d6",
        "rolls": 2,
        "items": [
            {"weight": 30, "item": None},
            {"weight": 25, "item": "sword"},
            {"weight": 20, "item": "shield"},
            {"weight": 15, "item": "potion_healing"},
            {"weight": 10, "item": "chain_mail"},
        ]
    },
    "ogre": {
        "gold_dice": "4d6",
        "rolls": 2,
        "items": [
            {"weight": 25, "item": None},
            {"weight": 25, "item": "potion_healing"},
            {"weight": 20, "item": "sword"},
            {"weight": 15, "item": "chain_mail"},
            {"weight": 15, "item": "golden_key"},
        ]
    },
    # Dangerous enemies
    "troll": {
        "gold_dice": "5d6",
        "rolls": 2,
        "items": [
            {"weight": 20, "item": None},
            {"weight": 30, "item": "potion_healing"},
            {"weight": 25, "item": "sword"},
            {"weight": 15, "item": "chain_mail"},
            {"weight": 10, "item": "golden_key"},
        ]
    },
    "wight": {
        "gold_dice": "3d6",
        "rolls": 2,
        "items": [
            {"weight": 30, "item": None},
            {"weight": 25, "item": "ancient_scroll"},
            {"weight": 20, "item": "golden_key"},
            {"weight": 15, "item": "potion_healing"},
            {"weight": 10, "item": "sword"},
        ]
    },
    "wraith": {
        "gold_dice": "4d6",
        "rolls": 2,
        "items": [
            {"weight": 35, "item": None},
            {"weight": 30, "item": "ancient_scroll"},
            {"weight": 20, "item": "golden_key"},
            {"weight": 15, "item": "potion_healing"},
        ]
    },
    # Boss enemies
    "vampire": {
        "gold_dice": "10d6",
        "rolls": 3,
        "items": [
            {"weight": 10, "item": None},
            {"weight": 30, "item": "potion_healing"},
            {"weight": 25, "item": "golden_key"},
            {"weight": 20, "item": "ancient_scroll"},
            {"weight": 15, "item": "chain_mail"},
        ]
    },
    "dragon": {
        "gold_dice": "20d6",
        "rolls": 4,
        "items": [
            {"weight": 5, "item": None},
            {"weight": 30, "item": "potion_healing"},
            {"weight": 25, "item": "golden_key"},
            {"weight": 20, "item": "sword"},
            {"weight": 20, "item": "chain_mail"},
        ]
    },
    # Fallback for unknown enemies
    "unknown_enemy": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 70, "item": None},
            {"weight": 20, "item": "rations"},
            {"weight": 10, "item": "torch"},
        ]
    },
}


def weighted_random_choice(items: list[dict]) -> str | None:
    """Select item from weighted list.

    Args:
        items: List of {"weight": int, "item": str|None}

    Returns:
        Selected item ID or None
    """
    total_weight = sum(entry["weight"] for entry in items)
    roll = random.randint(1, total_weight)

    cumulative = 0
    for entry in items:
        cumulative += entry["weight"]
        if roll <= cumulative:
            return entry["item"]

    return None  # Shouldn't happen


def roll_enemy_loot(enemy_type: str) -> dict:
    """Roll loot for a single defeated enemy.

    Args:
        enemy_type: Enemy type key (e.g., "goblin", "skeleton")

    Returns:
        Dict with "gold" (int) and "items" (list[str])
    """
    # Normalize enemy type for lookup
    normalized = enemy_type.lower().strip().replace(" ", "_")

    table = LOOT_TABLES.get(normalized, LOOT_TABLES["unknown_enemy"])

    # Roll gold
    gold = 0
    if table["gold_dice"] != "0d0":
        try:
            gold, _ = roll_dice(table["gold_dice"])
            gold = max(0, gold)
        except ValueError:
            gold = 0

    # Roll items
    items = []
    for _ in range(table["rolls"]):
        item = weighted_random_choice(table["items"])
        if item:
            items.append(item)

    logger.debug(
        "Rolled enemy loot",
        extra={
            "enemy_type": normalized,
            "gold": gold,
            "items": items,
        }
    )

    return {"gold": gold, "items": items}


def roll_combat_loot(defeated_enemies: list[dict]) -> dict:
    """Roll loot for all defeated enemies in combat.

    Args:
        defeated_enemies: List of enemy dicts with "name" field

    Returns:
        Combined loot dict with "gold" (int), "items" (list[str]), "source" (str)
    """
    total_gold = 0
    all_items = []

    for enemy in defeated_enemies:
        enemy_name = enemy.get("name", "unknown")
        # Strip numbering (e.g., "Goblin 1" -> "goblin")
        base_name = enemy_name.split()[0] if enemy_name else "unknown"

        loot = roll_enemy_loot(base_name)
        total_gold += loot["gold"]
        all_items.extend(loot["items"])

    logger.info(
        "Rolled combat loot",
        extra={
            "enemy_count": len(defeated_enemies),
            "total_gold": total_gold,
            "items": all_items,
        }
    )

    return {
        "gold": total_gold,
        "items": all_items,
        "source": "combat_victory",
    }


def get_loot_table(enemy_type: str) -> dict | None:
    """Get loot table for an enemy type.

    Args:
        enemy_type: Enemy type key

    Returns:
        Loot table dict or None if not found
    """
    normalized = enemy_type.lower().strip().replace(" ", "_")
    return LOOT_TABLES.get(normalized)
