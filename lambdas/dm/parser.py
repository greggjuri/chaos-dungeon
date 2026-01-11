"""Parser for extracting structured data from DM responses."""

import json
import re
from typing import Any

from aws_lambda_powertools import Logger
from pydantic import ValidationError

from .combat_narrator import clean_narrator_output
from .models import DiceRoll, DMResponse, Enemy, StateChanges

logger = Logger(child=True)

# Pattern to find JSON code blocks in the response
JSON_BLOCK_PATTERN = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)

# Pattern to find raw JSON objects (Mistral may not use code blocks)
RAW_JSON_PATTERN = re.compile(r"\{[\s\S]*\"state_changes\"[\s\S]*\}", re.DOTALL)


def parse_dm_response(response_text: str) -> DMResponse:
    """Parse AI response into structured data.

    Extracts the narrative portion and any JSON state changes
    from the DM's response. Handles both Claude and Mistral formats:
    - Code blocks with ```json
    - Raw JSON objects

    If JSON parsing fails, returns the narrative only with empty state changes.

    Args:
        response_text: Raw response text from AI model

    Returns:
        Parsed DMResponse with narrative and state changes
    """
    if not response_text or not response_text.strip():
        return DMResponse(narrative="")

    # First, try to find JSON in code blocks (preferred format)
    match = JSON_BLOCK_PATTERN.search(response_text)

    if match:
        # Extract narrative (everything before the JSON block)
        narrative = response_text[: match.start()].strip()
        # Clean artifacts from narrative
        narrative = clean_narrator_output(narrative)
        json_str = match.group(1)

        try:
            data = json.loads(json_str)
            return _build_response(narrative, data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from code block: {e}")
        except ValidationError as e:
            logger.warning(f"Failed to validate DM response data: {e}")

    # Try raw JSON (Mistral may not use code blocks)
    raw_match = RAW_JSON_PATTERN.search(response_text)
    if raw_match:
        narrative = response_text[: raw_match.start()].strip()
        # Clean artifacts from narrative
        narrative = clean_narrator_output(narrative)
        json_str = raw_match.group()

        try:
            data = json.loads(json_str)
            return _build_response(narrative, data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse raw JSON from DM response: {e}")
        except ValidationError as e:
            logger.warning(f"Failed to validate raw JSON data: {e}")

    # Fallback: return narrative only with empty state changes
    logger.debug("No JSON found in response, using narrative only")
    # Clean artifacts from narrative
    cleaned_narrative = clean_narrator_output(response_text.strip())
    return DMResponse(narrative=cleaned_narrative or response_text.strip())


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
    dice_rolls = [DiceRoll(**roll_data) for roll_data in data.get("dice_rolls", [])]

    # Parse enemies
    enemies_data = data.get("enemies", [])
    enemies = [Enemy(**enemy_data) for enemy_data in enemies_data]

    # Get combat status
    combat_active = data.get("combat_active", False)

    logger.debug(
        "Parsed DM response JSON",
        extra={
            "combat_active": combat_active,
            "enemies_count": len(enemies),
            "enemies_raw": enemies_data,
            "state_changes": state_data,
        },
    )

    return DMResponse(
        narrative=narrative,
        state_changes=state_changes,
        dice_rolls=dice_rolls,
        combat_active=combat_active,
        enemies=enemies,
    )
