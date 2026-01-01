"""Parser for extracting structured data from DM responses."""

import json
import re
from typing import Any

from aws_lambda_powertools import Logger
from pydantic import ValidationError

from .models import DiceRoll, DMResponse, Enemy, StateChanges

logger = Logger(child=True)

# Pattern to find JSON code blocks in the response
JSON_BLOCK_PATTERN = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def parse_dm_response(response_text: str) -> DMResponse:
    """Parse Claude's response into structured data.

    Extracts the narrative portion and any JSON state changes
    from the DM's response. If JSON parsing fails, returns
    the narrative only with empty state changes.

    Args:
        response_text: Raw response text from Claude

    Returns:
        Parsed DMResponse with narrative and state changes
    """
    if not response_text or not response_text.strip():
        return DMResponse(narrative="")

    # Find JSON block in response
    match = JSON_BLOCK_PATTERN.search(response_text)

    if match:
        # Extract narrative (everything before the JSON block)
        narrative = response_text[: match.start()].strip()
        json_str = match.group(1)

        try:
            data = json.loads(json_str)
            return _build_response(narrative, data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from DM response: {e}")
        except ValidationError as e:
            logger.warning(f"Failed to validate DM response data: {e}")

    # Fallback: return narrative only with empty state changes
    return DMResponse(narrative=response_text.strip())


def _build_response(narrative: str, data: dict[str, Any]) -> DMResponse:
    """Build a DMResponse from parsed JSON data.

    Args:
        narrative: The narrative portion of the response
        data: Parsed JSON data

    Returns:
        Constructed DMResponse
    """
    # Parse state changes
    state_data = data.get("state_changes", {})
    state_changes = StateChanges(**state_data)

    # Parse dice rolls
    dice_rolls = [
        DiceRoll(**roll_data) for roll_data in data.get("dice_rolls", [])
    ]

    # Parse enemies
    enemies = [Enemy(**enemy_data) for enemy_data in data.get("enemies", [])]

    # Get combat status
    combat_active = data.get("combat_active", False)

    return DMResponse(
        narrative=narrative,
        state_changes=state_changes,
        dice_rolls=dice_rolls,
        combat_active=combat_active,
        enemies=enemies,
    )
