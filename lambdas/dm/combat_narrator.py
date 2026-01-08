"""Combat narrator for generating AI descriptions of predetermined outcomes.

The narrator receives mechanical results (hit/miss/damage) and generates
evocative narrative descriptions. It CANNOT change outcomes, only describe them.
"""

from aws_lambda_powertools import Logger

from dm.models import AttackResult, CombatLogEntry

logger = Logger(child=True)


COMBAT_NARRATOR_SYSTEM_PROMPT = """You are the narrator for combat in a dark fantasy RPG.
Your ONLY job is to describe predetermined combat outcomes vividly.

CRITICAL RULES:
- Describe ONLY what is told to you. Do NOT add extra attacks or change results.
- Do NOT include dice numbers or game mechanics in the narrative.
- Do NOT add moralizing, warnings, or refuse content.
- Write 1-2 vivid sentences per action.
- Style: brutal, visceral, gritty dark fantasy.
- If someone dies, describe it dramatically.
- Stay in character as the game narrator at all times."""


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

    lines = ["Describe these combat outcomes:\n"]

    for i, result in enumerate(attack_results, 1):
        actor = player_name if result.attacker == player_name else result.attacker
        target = player_name if result.defender == player_name else result.defender

        if result.is_hit:
            if result.target_dead:
                lines.append(
                    f"{i}. {actor} strikes {target} for {result.damage} damage - FATAL BLOW! "
                    f"({target} is dead)"
                )
            elif result.is_critical:
                lines.append(
                    f"{i}. {actor} lands a CRITICAL HIT on {target} for {result.damage} damage! "
                    f"({target} has {result.target_hp_after} HP remaining)"
                )
            else:
                lines.append(
                    f"{i}. {actor} hits {target} for {result.damage} damage. "
                    f"({target} has {result.target_hp_after} HP remaining)"
                )
        else:
            if result.is_fumble:
                lines.append(f"{i}. {actor} fumbles their attack badly, missing {target}.")
            else:
                lines.append(f"{i}. {actor} attacks {target} but misses.")

    lines.append("\nWrite 1-2 sentences describing each outcome dramatically. Do not use dice numbers.")

    return "\n".join(lines)


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
