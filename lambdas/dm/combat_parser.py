"""Parser for converting free text to structured combat actions.

Handles natural language input like "attack the goblin" or "run away"
and converts to structured CombatAction objects.
"""

import re

from aws_lambda_powertools import Logger

from dm.models import CombatAction, CombatActionType, CombatEnemy

logger = Logger(child=True)

# Keywords for action detection
ATTACK_KEYWORDS = [
    "attack",
    "hit",
    "strike",
    "kill",
    "fight",
    "slash",
    "stab",
    "swing",
    "shoot",
    "smash",
    "cleave",
]
DEFEND_KEYWORDS = ["defend", "block", "guard", "brace", "shield", "parry", "dodge"]
FLEE_KEYWORDS = ["flee", "run", "escape", "retreat", "leave", "get out", "run away"]
ITEM_KEYWORDS = ["drink", "use", "potion", "heal", "consume", "apply", "take"]


def parse_combat_action(
    text: str,
    enemies: list[CombatEnemy],
) -> CombatAction | None:
    """Parse free text into structured combat action.

    Args:
        text: Player's free text input (e.g., "attack the goblin")
        enemies: List of living enemies to match target against

    Returns:
        CombatAction if recognized, None if unrecognized

    Examples:
        "attack goblin" -> CombatAction(type=ATTACK, target_id="<goblin_id>")
        "run away" -> CombatAction(type=FLEE)
        "defend" -> CombatAction(type=DEFEND)
        "drink potion" -> CombatAction(type=USE_ITEM)
    """
    if not text:
        return None

    normalized = text.lower().strip()

    logger.debug(
        "Parsing combat action",
        extra={"text": normalized, "enemies_count": len(enemies)},
    )

    # Check for defend action
    if _contains_any(normalized, DEFEND_KEYWORDS):
        logger.info("Parsed action: DEFEND")
        return CombatAction(action_type=CombatActionType.DEFEND)

    # Check for flee action
    if _contains_any(normalized, FLEE_KEYWORDS):
        logger.info("Parsed action: FLEE")
        return CombatAction(action_type=CombatActionType.FLEE)

    # Check for item usage
    if _contains_any(normalized, ITEM_KEYWORDS):
        logger.info("Parsed action: USE_ITEM")
        return CombatAction(action_type=CombatActionType.USE_ITEM)

    # Check for attack action
    if _contains_any(normalized, ATTACK_KEYWORDS):
        target = _find_target(normalized, enemies)
        if target:
            logger.info(
                "Parsed action: ATTACK",
                extra={"target_id": target.id, "target_name": target.name},
            )
            return CombatAction(
                action_type=CombatActionType.ATTACK,
                target_id=target.id,
            )
        # Attack without valid target - will use first enemy as default
        logger.info("Parsed action: ATTACK (no target specified)")
        return CombatAction(action_type=CombatActionType.ATTACK)

    # No recognized action
    logger.debug("No combat action recognized from text")
    return None


def get_default_action(enemies: list[CombatEnemy]) -> CombatAction:
    """Get a default combat action when text can't be parsed.

    Defaults to attacking the first living enemy.

    Args:
        enemies: List of enemies in combat

    Returns:
        CombatAction to attack first living enemy
    """
    living = [e for e in enemies if e.hp > 0]
    target_id = living[0].id if living else None

    return CombatAction(
        action_type=CombatActionType.ATTACK,
        target_id=target_id,
    )


def get_valid_targets(enemies: list[CombatEnemy]) -> list[str]:
    """Get list of valid target IDs (living enemies).

    Args:
        enemies: List of all enemies in combat

    Returns:
        List of enemy IDs that can be targeted
    """
    return [e.id for e in enemies if e.hp > 0]


def _contains_any(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the keywords.

    Args:
        text: Normalized (lowercase) text to check
        keywords: List of keywords to look for

    Returns:
        True if any keyword found
    """
    return any(keyword in text for keyword in keywords)


def _find_target(text: str, enemies: list[CombatEnemy]) -> CombatEnemy | None:
    """Find target enemy from player's text input.

    Matching priority:
    1. Full name match (case-insensitive): "Goblin 1" matches "Goblin 1"
    2. First word match: "goblin" matches "Goblin 1" (first living match)
    3. Numbered suffix: "2" matches enemy with " 2" suffix

    If multiple enemies match (e.g., "attack goblin" with Goblin 1 and Goblin 2),
    returns the FIRST living enemy in list order.

    Args:
        text: Player's input text
        enemies: List of enemies in combat

    Returns:
        First matching living enemy, or None
    """
    text_lower = text.lower().strip()
    living_enemies = [e for e in enemies if e.hp > 0]

    if not living_enemies:
        return None

    # 1. Full name match (exact or contained in text)
    for enemy in living_enemies:
        if enemy.name.lower() == text_lower or enemy.name.lower() in text_lower:
            return enemy

    # 2. First word match (e.g., "goblin" matches "Goblin 1")
    for enemy in living_enemies:
        first_word = enemy.name.split()[0].lower()
        if first_word in text_lower:
            return enemy  # Return FIRST match

    # 3. Numbered suffix match (e.g., "attack 2" targets enemy with " 2" suffix)
    # Use exact suffix match to avoid "1" matching "Goblin 11"
    match = re.search(r"\b(\d+)\b", text)
    if match:
        num = match.group(1)
        for enemy in living_enemies:
            if enemy.name.endswith(f" {num}"):
                return enemy

    return None
