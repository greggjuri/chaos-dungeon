"""Combat narrator for generating AI descriptions of predetermined outcomes.

The narrator receives mechanical results (hit/miss/damage) and generates
evocative narrative descriptions. It CANNOT change outcomes, only describe them.
"""

import re

from aws_lambda_powertools import Logger

from dm.models import AttackResult, CombatLogEntry

logger = Logger(child=True)

# Patterns that indicate prompt leakage - should be stripped from output
PROMPT_LEAK_PATTERNS = [
    r"^Player action:.*$",
    r"^Narrate:.*$",
    r"^Write \d+-?\d* sentences?.*$",
    r"^Describe (these|the|each).*:?\s*$",
    r"^Respond as.*$",
    r"^Output.*narrative.*$",
    r"^\d+\.\s+(Human|Player|Wizard|Rogue|Paladin|Cleric|Fighter).*casts?.*$",
    r"^Here'?s? (the|a) narrative.*:?\s*$",
    # Additional patterns for Mistral leakage
    r"^Dungeon Master\.?$",
    r"^\d+\.\s+\w+\s+(hits|misses|strikes|kills|crits|fumbles).*\(\d+\s*(damage|HP).*\).*$",
    r".*\(\w+\s+has\s+\d+\s+HP\s+remaining\).*$",
    r"^.*dealing\s+\d+\s+damage.*$",
    # Output format artifacts
    r"^Narrative:?\s*$",
    r"^State Changes:?\s*$",
    r"^```.*$",
    r"^---+$",
    r"^\*\*.*\*\*:?\s*$",  # Markdown bold headers
]

# Patterns to clean from within narrative text (not line-based)
HP_LEAK_PATTERNS = [
    r"\s*\(?\d+\s*HP\s*(remaining|left)?\)?\.?",  # "(15 HP remaining)"
    r"\s*\(?remaining\s+health\s+(now\s+)?at\s+\d+\)?\.?",  # "remaining health now at 15"
    r"\s*\(?health\s*:\s*\d+\)?\.?",  # "health: 15"
    r"\s*\(?\w+\s+has\s+\d+\s*(HP|health|hit\s*points?)\s*(remaining|left)?\)?\.?",  # "Goblin has 5 HP"
    r"\s*\(?now\s+at\s+\d+\s*(HP|health)\)?\.?",  # "now at 15 HP"
]


def clean_narrator_output(text: str) -> str:
    """Clean AI output by removing any prompt leakage.

    Args:
        text: Raw AI response text

    Returns:
        Cleaned narrative text
    """
    if not text:
        return ""

    lines = text.strip().split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line matches any prompt leak pattern
        is_prompt_leak = False
        for pattern in PROMPT_LEAK_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                is_prompt_leak = True
                logger.warning(f"Stripped prompt leak: {line[:50]}...")
                break

        if not is_prompt_leak:
            cleaned_lines.append(line)

    result = " ".join(cleaned_lines)

    # Clean HP/health leaks from within the text
    for pattern in HP_LEAK_PATTERNS:
        original = result
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
        if result != original:
            logger.warning(f"Cleaned HP leak with pattern: {pattern[:30]}...")

    # Clean up any double spaces or awkward punctuation from removal
    result = re.sub(r"\s{2,}", " ", result)  # Multiple spaces to single
    result = re.sub(r"\s+([.,!?])", r"\1", result)  # Space before punctuation
    result = re.sub(r"([.,!?])\s*([.,!?])", r"\1", result)  # Double punctuation

    # If we stripped everything, return a fallback
    if not result.strip():
        logger.warning("All output was prompt leakage, using fallback")
        return ""

    return result.strip()


COMBAT_NARRATOR_SYSTEM_PROMPT = """You are a combat narrator for a dark fantasy RPG. Describe combat outcomes vividly.

RULES:
- Output ONLY narrative prose. No meta-commentary, no instructions, no "Player action:" prefixes.
- Describe exactly what is given - do not invent extra party members or attacks.
- NEVER mention HP, health points, damage numbers, or remaining health. NO NUMBERS.
- No dice numbers or game mechanics in output.
- 1-2 vivid sentences per action. Brutal, visceral style.
- Describe deaths dramatically.
- Output the narrative directly with no preamble."""


def build_narrator_prompt(attack_results: list[AttackResult], player_name: str) -> str:
    """Build a minimal prompt for the AI to narrate combat outcomes.

    Args:
        attack_results: List of resolved attacks to narrate
        player_name: Name of the player character

    Returns:
        Prompt string for the AI
    """
    if not attack_results:
        return "The combatants circle each other warily, waiting for an opening."

    lines = []

    for result in attack_results:
        actor = result.attacker
        target = result.defender

        if result.is_hit:
            if result.target_dead:
                lines.append(f"{actor} kills {target} ({result.damage} damage)")
            elif result.is_critical:
                lines.append(f"{actor} crits {target} ({result.damage} damage)")
            else:
                lines.append(f"{actor} hits {target} ({result.damage} damage)")
        else:
            if result.is_fumble:
                lines.append(f"{actor} fumbles against {target}")
            else:
                lines.append(f"{actor} misses {target}")

    return "Narrate: " + "; ".join(lines)


def build_defend_narrative() -> str:
    """Build narrative for a defend action.

    Returns:
        Short narrative for defending.
    """
    return "You raise your guard, bracing for the enemy's assault."


def build_flee_narrative(success: bool) -> str:
    """Build narrative for a flee attempt.

    Args:
        success: Whether the flee attempt succeeded

    Returns:
        Narrative describing the escape attempt
    """
    if success:
        return (
            "You seize an opening in the chaos of battle and break away, "
            "your feet pounding against the ground as you flee to safety."
        )
    else:
        return (
            "You attempt to disengage and flee, but the enemies cut off your escape route. "
            "You must continue fighting!"
        )


def build_combat_log_entries(
    attack_results: list[AttackResult],
    round_num: int,
    player_name: str,
    narrative: str = "",
) -> list[CombatLogEntry]:
    """Convert attack results to combat log entries.

    Args:
        attack_results: List of resolved attacks
        round_num: Current round number
        player_name: Name of player character
        narrative: Optional narrative to include

    Returns:
        List of CombatLogEntry for the combat log
    """
    entries = []

    for result in attack_results:
        is_player = result.attacker == player_name
        actor = "player" if is_player else result.attacker

        if result.is_hit:
            if result.target_dead:
                result_str = "killed"
            else:
                result_str = "hit"
        else:
            result_str = "miss"

        entries.append(
            CombatLogEntry(
                round=round_num,
                actor=actor,
                action="attack",
                target=result.defender,
                roll=result.attack_total,
                damage=result.damage if result.is_hit else None,
                result=result_str,
                narrative=narrative if is_player else "",
            )
        )

    return entries


def build_defend_log_entry(round_num: int) -> CombatLogEntry:
    """Build a combat log entry for a defend action.

    Args:
        round_num: Current round number

    Returns:
        CombatLogEntry for defending
    """
    return CombatLogEntry(
        round=round_num,
        actor="player",
        action="defend",
        target=None,
        roll=None,
        damage=None,
        result="defended",
        narrative="You raise your guard, gaining +2 AC this round.",
    )


def build_flee_log_entry(round_num: int, success: bool) -> CombatLogEntry:
    """Build a combat log entry for a flee attempt.

    Args:
        round_num: Current round number
        success: Whether the flee succeeded

    Returns:
        CombatLogEntry for the flee attempt
    """
    return CombatLogEntry(
        round=round_num,
        actor="player",
        action="flee",
        target=None,
        roll=None,
        damage=None,
        result="fled" if success else "failed",
        narrative=build_flee_narrative(success),
    )
