"""Server-side combat resolution following BECMI D&D rules.

This module handles all combat mechanics on the server to ensure
fair, consistent outcomes. Claude receives the results to narrate,
not choices to make.
"""

import random

from aws_lambda_powertools import Logger

from dm.models import AttackResult, CombatEnemy, CombatRoundResult, CombatState
from shared.dice import roll
from shared.utils import calculate_modifier

logger = Logger(child=True)


class CombatResolver:
    """Server-side combat resolution following BECMI rules.

    Handles attack rolls, damage calculation, and combat round resolution.
    All dice rolling happens here, not in Claude's response.
    """

    def resolve_player_attack(
        self,
        character: dict,
        target: CombatEnemy,
    ) -> AttackResult:
        """Resolve player attacking an enemy.

        Uses STR modifier for melee attacks. Critical hits (nat 20) always hit,
        fumbles (nat 1) always miss.

        Args:
            character: Character dict with name, hp, stats
            target: Enemy being attacked

        Returns:
            AttackResult with full breakdown of the attack
        """
        # Get STR modifier for melee
        str_mod = calculate_modifier(character["stats"]["strength"])
        attack_bonus = str_mod  # Could add level bonuses later

        # Roll attack
        total, natural = self._roll_attack(attack_bonus)

        # Determine hit/miss
        # Nat 1 always misses, nat 20 always hits
        is_fumble = natural == 1
        is_crit = natural == 20
        is_hit = not is_fumble and (is_crit or total >= target.ac)

        damage = 0
        damage_rolls: list[int] = []
        hp_before = target.hp

        if is_hit:
            # Roll damage
            weapon_dice = self._get_weapon_damage(character)
            damage, damage_rolls = roll(weapon_dice)
            damage = max(1, damage + str_mod)  # Minimum 1 damage on hit
            target.hp = max(0, target.hp - damage)

        logger.debug(
            "Player attack resolved",
            extra={
                "attacker": character["name"],
                "defender": target.name,
                "roll": natural,
                "total": total,
                "is_hit": is_hit,
                "damage": damage,
            },
        )

        return AttackResult(
            attacker=character["name"],
            defender=target.name,
            attack_roll=natural,
            attack_bonus=attack_bonus,
            attack_total=total,
            target_ac=target.ac,
            is_hit=is_hit,
            is_critical=is_crit,
            is_fumble=is_fumble,
            damage=damage,
            damage_rolls=damage_rolls,
            target_hp_before=hp_before,
            target_hp_after=target.hp,
            target_dead=target.hp <= 0,
        )

    def resolve_enemy_attack(
        self,
        enemy: CombatEnemy,
        character: dict,
    ) -> AttackResult:
        """Resolve enemy attacking the player.

        Uses enemy's attack bonus vs player's AC (10 + DEX mod).

        Args:
            enemy: Attacking enemy
            character: Character dict being attacked

        Returns:
            AttackResult with full breakdown of the attack
        """
        player_ac = self._calculate_player_ac(character)

        # Roll attack
        total, natural = self._roll_attack(enemy.attack_bonus)

        # Determine hit/miss
        is_fumble = natural == 1
        is_crit = natural == 20
        is_hit = not is_fumble and (is_crit or total >= player_ac)

        damage = 0
        damage_rolls: list[int] = []
        hp_before = character["hp"]
        hp_after = hp_before

        if is_hit:
            damage, damage_rolls = roll(enemy.damage_dice)
            damage = max(1, damage)  # Minimum 1 damage on hit
            hp_after = max(0, hp_before - damage)

        logger.debug(
            "Enemy attack resolved",
            extra={
                "attacker": enemy.name,
                "defender": character["name"],
                "roll": natural,
                "total": total,
                "is_hit": is_hit,
                "damage": damage,
            },
        )

        return AttackResult(
            attacker=enemy.name,
            defender=character["name"],
            attack_roll=natural,
            attack_bonus=enemy.attack_bonus,
            attack_total=total,
            target_ac=player_ac,
            is_hit=is_hit,
            is_critical=is_crit,
            is_fumble=is_fumble,
            damage=damage,
            damage_rolls=damage_rolls,
            target_hp_before=hp_before,
            target_hp_after=hp_after,
            target_dead=hp_after <= 0,
        )

    def resolve_combat_round(
        self,
        character: dict,
        combat_state: CombatState,
        combat_enemies: list[CombatEnemy],
    ) -> CombatRoundResult:
        """Resolve a full combat round.

        In BECMI, each side acts once per round based on initiative.
        Higher initiative goes first.

        Args:
            character: Character dict (modified in place for HP)
            combat_state: Current combat state with initiative
            combat_enemies: List of enemies (modified in place for HP)

        Returns:
            CombatRoundResult with all attack outcomes
        """
        results: list[AttackResult] = []
        xp_gained = 0

        # Determine attack order
        player_first = combat_state.player_initiative >= combat_state.enemy_initiative
        living_enemies = [e for e in combat_enemies if e.hp > 0]

        logger.info(
            "Resolving combat round",
            extra={
                "round": combat_state.round,
                "player_first": player_first,
                "living_enemies": len(living_enemies),
            },
        )

        if player_first:
            # Player attacks first
            if living_enemies and character["hp"] > 0:
                target = living_enemies[0]  # Attack first enemy
                result = self.resolve_player_attack(character, target)
                results.append(result)
                if result.target_dead:
                    xp_gained += target.xp_value
                    logger.info(
                        "Enemy defeated",
                        extra={"enemy": target.name, "xp": target.xp_value},
                    )

            # Surviving enemies counterattack
            for enemy in living_enemies:
                if enemy.hp > 0 and character["hp"] > 0:
                    result = self.resolve_enemy_attack(enemy, character)
                    results.append(result)
                    if result.is_hit:
                        character["hp"] = result.target_hp_after
        else:
            # Enemies attack first
            for enemy in living_enemies:
                if character["hp"] > 0:
                    result = self.resolve_enemy_attack(enemy, character)
                    results.append(result)
                    if result.is_hit:
                        character["hp"] = result.target_hp_after

            # Player counterattacks if alive
            living_enemies = [e for e in combat_enemies if e.hp > 0]
            if character["hp"] > 0 and living_enemies:
                target = living_enemies[0]
                result = self.resolve_player_attack(character, target)
                results.append(result)
                if result.target_dead:
                    xp_gained += target.xp_value
                    logger.info(
                        "Enemy defeated",
                        extra={"enemy": target.name, "xp": target.xp_value},
                    )

        # Check end conditions
        remaining = [e for e in combat_enemies if e.hp > 0]
        player_dead = character["hp"] <= 0
        combat_ended = len(remaining) == 0 or player_dead

        if player_dead:
            logger.warning(
                "Player died in combat",
                extra={"character": character["name"], "round": combat_state.round},
            )
        elif len(remaining) == 0:
            logger.info(
                "All enemies defeated",
                extra={"round": combat_state.round, "xp_total": xp_gained},
            )

        return CombatRoundResult(
            round=combat_state.round,
            attack_results=results,
            player_hp=character["hp"],
            player_dead=player_dead,
            enemies_remaining=remaining,
            combat_ended=combat_ended,
            xp_gained=xp_gained,
        )

    def _roll_attack(self, bonus: int) -> tuple[int, int]:
        """Roll d20 attack.

        Args:
            bonus: Attack bonus to add

        Returns:
            Tuple of (total, natural_roll)
        """
        natural = random.randint(1, 20)
        return natural + bonus, natural

    def _calculate_player_ac(self, character: dict) -> int:
        """Calculate player's AC.

        Base 10 + DEX modifier. Armor bonuses would be added from inventory.

        Args:
            character: Character dict with stats

        Returns:
            Calculated AC
        """
        dex_mod = calculate_modifier(character["stats"]["dexterity"])
        # TODO: Add armor bonuses from inventory
        return 10 + dex_mod

    def _get_weapon_damage(self, character: dict) -> str:
        """Get weapon damage dice.

        Currently returns default 1d6. Would look up equipped weapon.

        Args:
            character: Character dict with inventory

        Returns:
            Damage dice notation
        """
        # TODO: Look up equipped weapon from inventory
        return "1d6"
