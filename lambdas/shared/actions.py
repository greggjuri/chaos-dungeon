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

# Patterns to detect sell attempts
SELL_PATTERNS = [
    r"\bsell\b",
    r"\btrade\b.*\bfor\b.*\bgold\b",
    r"\bexchange\b.*\bfor\b.*\b(gold|coins?)\b",
    r"\bpawn\b",
    r"\bget\s+(rid\s+of|gold\s+for)\b",
    r"\bgive\b.*\bfor\b.*\b(gold|coins?|money)\b",
]

# Patterns to detect buy attempts
# NOTE: "acquire" removed - too ambiguous ("acquire gold for my item" = sell)
BUY_PATTERNS = [
    r"\bbuy\b",
    r"\bpurchase\b",
    r"\bpay\b.*\bfor\b",
    r"\bget\b.*\bfrom\b.*\b(shop|merchant|vendor|store)\b",
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


def is_sell_action(action: str) -> bool:
    """Detect if player is trying to sell something.

    Args:
        action: Player action text

    Returns:
        True if action appears to be a sell attempt
    """
    action_lower = action.lower()
    for pattern in SELL_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("COMMERCE: Sell action detected", extra={
                "action": action[:100],
                "matched_pattern": pattern,
            })
            return True
    return False


def is_buy_action(action: str) -> bool:
    """Detect if player is trying to buy something.

    Args:
        action: Player action text

    Returns:
        True if action appears to be a buy attempt
    """
    action_lower = action.lower()
    for pattern in BUY_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("COMMERCE: Buy action detected", extra={
                "action": action[:100],
                "matched_pattern": pattern,
            })
            return True
    return False


# Patterns to detect attack intent
ATTACK_PATTERNS = [
    r"\battack\b",
    r"\bstrike\b",
    r"\bstab\b",
    r"\bkill\b",
    r"\bhit\b",
    r"\bpunch\b",
    r"\bkick\b",
    r"\bslash\b",
    r"\bshoot\b",
    r"\bswing\b.*\bat\b",
    r"\bsword\b.*\bat\b",
    r"\bblade\b.*\binto\b",
    r"\barrow\b.*\bat\b",
]

# Confirmation response patterns
CONFIRM_PATTERNS = [
    r"\byes\b",
    r"\byeah\b",
    r"\byep\b",
    r"\bsure\b",
    r"\bdo\s+it\b",
    r"\bproceed\b",
    r"\bconfirm\b",
]

CANCEL_PATTERNS = [
    r"\bno\b",
    r"\bnope\b",
    r"\bnevermind\b",
    r"\bcancel\b",
    r"\bstop\b",
    r"\bwait\b",
    r"\bdon'?t\b",
]


def is_attack_action(action: str) -> bool:
    """Detect if player action is an attack attempt.

    Args:
        action: Player action text

    Returns:
        True if action appears to be an attack
    """
    action_lower = action.lower()
    for pattern in ATTACK_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("COMBAT: Attack action detected", extra={
                "action": action[:100],
                "matched_pattern": pattern,
            })
            return True
    return False


def extract_attack_target(action: str) -> str | None:
    """Extract the target from an attack action (best effort).

    Args:
        action: Player action text

    Returns:
        Target name/description, or None if not found
    """
    # Match patterns like "attack the shopkeeper", "stab him", "kill the guard"
    patterns = [
        r"(?:attack|strike|stab|kill|hit|punch|kick|slash|shoot)\s+(?:the\s+)?(.+?)(?:\s+with|\s*$)",
        r"(?:swing|sword|blade|arrow)\s+(?:at|into)\s+(?:the\s+)?(.+?)(?:\s+with|\s*$)",
    ]
    action_lower = action.lower()
    for pattern in patterns:
        match = re.search(pattern, action_lower)
        if match:
            target = match.group(1).strip()
            logger.debug("COMBAT: Extracted target", extra={
                "action": action[:100],
                "target": target,
            })
            return target
    return None


def detect_confirmation_response(action: str) -> str:
    """Detect if action is a confirmation, cancellation, or new action.

    Args:
        action: Player action text

    Returns:
        "confirm" - Player confirmed the pending action
        "cancel" - Player cancelled
        "new_action" - This is a different action, clear pending state
    """
    action_lower = action.lower()

    # Check for explicit confirmation
    for pattern in CONFIRM_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("COMBAT: Confirmation detected", extra={"action": action[:100]})
            return "confirm"

    # Check for cancellation
    for pattern in CANCEL_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("COMBAT: Cancellation detected", extra={"action": action[:100]})
            return "cancel"

    # Check if this is another attack (counts as confirm)
    if is_attack_action(action):
        logger.info("COMBAT: Attack re-stated as confirmation", extra={
            "action": action[:100],
        })
        return "confirm"

    # Otherwise treat as new action
    logger.debug("COMBAT: New action, clearing pending", extra={"action": action[:100]})
    return "new_action"
