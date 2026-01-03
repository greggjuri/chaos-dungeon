"""Combat outcome prompt builder for Claude narration.

Builds prompts that tell Claude the mechanical outcome of combat.
Claude's job is ONLY to narrate these predetermined results - it cannot
change the outcome.
"""

from dm.models import AttackResult, CombatRoundResult


def build_combat_outcome_prompt(
    round_result: CombatRoundResult,
    player_name: str,
    player_max_hp: int,
) -> str:
    """Build a prompt telling Claude what happened in combat.

    The prompt instructs Claude to narrate the predetermined outcome
    without changing it. This ensures fair, mechanical combat.

    Args:
        round_result: The mechanically resolved combat round
        player_name: Character's name
        player_max_hp: Character's maximum HP

    Returns:
        Prompt string for Claude to narrate
    """
    lines = [
        "## COMBAT OUTCOME (NARRATE THIS EXACTLY)",
        "",
        "The following combat has been mechanically resolved. Your job is ONLY to",
        "narrate what happened in dramatic fashion. You CANNOT change the outcome.",
        "",
        f"Round {round_result.round}:",
        "",
    ]

    # Add each attack result
    for attack in round_result.attack_results:
        lines.append(_format_attack(attack))
        lines.append("")

    # Determine player status
    if round_result.player_dead:
        status = "DEAD"
    elif round_result.player_hp <= player_max_hp // 4:
        status = "Near death"
    elif round_result.player_hp <= player_max_hp // 2:
        status = "Badly wounded"
    elif round_result.player_hp < player_max_hp:
        status = "Wounded"
    else:
        status = "Unharmed"

    # Format enemy status
    if round_result.enemies_remaining:
        enemy_status = ", ".join(
            f"{e.name} ({e.hp}/{e.max_hp} HP)" for e in round_result.enemies_remaining
        )
    else:
        enemy_status = "All enemies defeated"

    lines.extend(
        [
            "FINAL STATE:",
            f"- {player_name} HP: {round_result.player_hp}/{player_max_hp}",
            f"- {player_name} Status: {status}",
            f"- Enemies: {enemy_status}",
            "",
        ]
    )

    # Add XP if any earned
    if round_result.xp_gained > 0:
        lines.append(f"XP Earned: {round_result.xp_gained}")
        lines.append("")

    # Add narration instructions based on outcome
    if round_result.player_dead:
        lines.extend(
            [
                "NARRATION INSTRUCTIONS:",
                f"Narrate {player_name}'s death dramatically. They are DEAD.",
                "Describe their final moments with grim finality.",
                "Do not soften or change the outcome. Death is permanent.",
            ]
        )
    elif round_result.combat_ended and len(round_result.enemies_remaining) == 0:
        lines.extend(
            [
                "NARRATION INSTRUCTIONS:",
                "All enemies have been defeated! Narrate the victory.",
                "Describe the aftermath and any loot that might be found.",
            ]
        )
    else:
        lines.extend(
            [
                "NARRATION INSTRUCTIONS:",
                "Narrate this combat round with vivid, dramatic detail.",
                "Combat continues - describe the ongoing battle.",
            ]
        )

    return "\n".join(lines)


def _format_attack(attack: AttackResult) -> str:
    """Format a single attack result for the prompt.

    Args:
        attack: The attack result to format

    Returns:
        Formatted string describing the attack
    """
    attacker_upper = attack.attacker.upper()
    lines = [f"{attacker_upper} ATTACK:"]
    lines.append(f"- {attack.attacker} attacks {attack.defender}")

    # Roll details
    roll_str = f"d20({attack.attack_roll})"
    if attack.attack_bonus >= 0:
        roll_str += f" + {attack.attack_bonus}"
    else:
        roll_str += f" - {abs(attack.attack_bonus)}"
    roll_str += f" = {attack.attack_total} vs AC {attack.target_ac}"
    lines.append(f"- Roll: {roll_str}")

    # Result
    if attack.is_fumble:
        lines.append("- FUMBLE - Critical failure!")
    elif attack.is_critical:
        damage_str = _format_damage_rolls(attack.damage_rolls, attack.damage)
        lines.append(f"- CRITICAL HIT! Damage: {damage_str}")
    elif attack.is_hit:
        damage_str = _format_damage_rolls(attack.damage_rolls, attack.damage)
        lines.append(f"- HIT - Damage: {damage_str}")
    else:
        lines.append("- MISS - The attack fails to connect")

    # Target status after attack
    if attack.is_hit:
        if attack.target_dead:
            lines.append(f"- {attack.defender} is SLAIN!")
        else:
            lines.append(f"- {attack.defender} HP: {attack.target_hp_after}")

    return "\n".join(lines)


def _format_damage_rolls(rolls: list[int], total: int) -> str:
    """Format damage rolls into a readable string.

    Args:
        rolls: Individual die results
        total: Total damage dealt

    Returns:
        Formatted damage string
    """
    if not rolls:
        return f"{total} HP"

    roll_str = "+".join(str(r) for r in rolls)
    if len(rolls) > 1:
        return f"({roll_str}) = {total} HP"
    return f"{total} HP"


def build_combat_context(
    player_name: str,
    player_hp: int,
    player_max_hp: int,
    enemies: list[dict],
    round_num: int,
) -> str:
    """Build context about ongoing combat for Claude.

    Used to remind Claude about the combat state when processing
    non-attack actions during combat.

    Args:
        player_name: Character's name
        player_hp: Current HP
        player_max_hp: Maximum HP
        enemies: List of enemy dicts
        round_num: Current combat round

    Returns:
        Combat context string
    """
    lines = [
        "## ACTIVE COMBAT",
        "",
        f"Combat Round: {round_num}",
        f"{player_name} HP: {player_hp}/{player_max_hp}",
        "",
        "Enemies:",
    ]

    for enemy in enemies:
        hp = enemy.get("hp", 0)
        max_hp = enemy.get("max_hp", hp)
        name = enemy.get("name", "Unknown")
        lines.append(f"- {name}: {hp}/{max_hp} HP")

    lines.extend(
        [
            "",
            "The player is in combat. Any attack actions will be resolved",
            "mechanically by the server. Narrate accordingly.",
        ]
    )

    return "\n".join(lines)
