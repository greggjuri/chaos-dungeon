"""Utility functions for Chaos Dungeon Lambda handlers."""
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def generate_id() -> str:
    """Generate a unique ID for resources.

    Returns:
        UUID string
    """
    return str(uuid4())


def utc_now() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO formatted timestamp string
    """
    return datetime.now(UTC).isoformat()


def extract_user_id(headers: dict[str, str]) -> str | None:
    """Extract user ID from request headers.

    Looks for the X-User-Id header (case-insensitive).

    Args:
        headers: Request headers dict

    Returns:
        User ID string or None if not found
    """
    # Headers may be case-insensitive
    for key, value in headers.items():
        if key.lower() == "x-user-id":
            return value
    return None


def api_response(
    status_code: int,
    body: dict[str, Any] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Format an API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body dict (optional)
        message: Simple message (used if body not provided)

    Returns:
        API Gateway response dict
    """
    import json

    response_body: dict[str, Any]
    if body is not None:
        response_body = body
    elif message is not None:
        response_body = {"message": message}
    else:
        response_body = {}

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(response_body),
    }


def error_response(
    status_code: int,
    error: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format an error response.

    Args:
        status_code: HTTP status code
        error: Error type/code
        message: Human-readable error message
        details: Optional additional error details

    Returns:
        API Gateway error response dict
    """
    body: dict[str, Any] = {
        "error": error,
        "message": message,
    }
    if details:
        body["details"] = details

    return api_response(status_code, body)


def roll_dice(num_dice: int, sides: int) -> list[int]:
    """Roll dice and return individual results.

    Args:
        num_dice: Number of dice to roll
        sides: Number of sides on each die

    Returns:
        List of individual roll results
    """
    import random

    return [random.randint(1, sides) for _ in range(num_dice)]


def roll_ability_scores() -> dict[str, int]:
    """Roll 3d6 for each ability score (BECMI style).

    Returns:
        Dict of ability name to score
    """
    abilities = ["strength", "intelligence", "wisdom", "dexterity", "constitution", "charisma"]
    return {ability: sum(roll_dice(3, 6)) for ability in abilities}


def calculate_modifier(score: int) -> int:
    """Calculate ability score modifier (BECMI style).

    BECMI uses a different modifier table than modern D&D:
    3: -3, 4-5: -2, 6-8: -1, 9-12: 0, 13-15: +1, 16-17: +2, 18: +3

    Args:
        score: Ability score (3-18)

    Returns:
        Modifier value
    """
    if score <= 3:
        return -3
    elif score <= 5:
        return -2
    elif score <= 8:
        return -1
    elif score <= 12:
        return 0
    elif score <= 15:
        return 1
    elif score <= 17:
        return 2
    else:
        return 3
