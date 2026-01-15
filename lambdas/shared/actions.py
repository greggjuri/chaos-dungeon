"""Action detection utilities for Chaos Dungeon."""

import re

from aws_lambda_powertools import Logger

logger = Logger(child=True)

# Patterns to detect search/loot attempts
# These are regex patterns that match player intent to search/loot
SEARCH_PATTERNS = [
    r"\bsearch\b",
    r"\bloot\b",
    r"\btake\b.*\b(body|bodies|corpse|stuff|items|gold|loot)\b",
    r"\bgrab\b.*\b(loot|gold|items|stuff)\b",
    r"\bcheck\b.*\b(body|bodies|corpse|pockets)\b",
    r"\bcollect\b.*\b(loot|gold)\b",
    r"\bgather\b.*\bloot\b",
    r"\brummage\b",
    r"\bpilfer\b",
]


def is_search_action(action: str) -> bool:
    """Detect if player action is attempting to search/loot.

    Used by the server to claim pending_loot when the player
    performs a search action after combat.

    Args:
        action: Player action text

    Returns:
        True if action appears to be a search/loot attempt
    """
    action_lower = action.lower()
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("LOOT_FLOW: Search action detected", extra={
                "action": action[:100],
                "matched_pattern": pattern,
            })
            return True

    logger.debug("LOOT_FLOW: Not a search action", extra={
        "action": action[:100],
    })
    return False
