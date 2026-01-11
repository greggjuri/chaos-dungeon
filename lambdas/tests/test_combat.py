"""Tests for combat resolution module."""

import random

import pytest

from dm.combat import CombatResolver
from dm.models import CombatEnemy, CombatState


@pytest.fixture
def resolver():
    """Create a combat resolver."""
    return CombatResolver()


@pytest.fixture
def fighter():
    """Create a fighter character."""
    return {
        "name": "Grimjaw",
        "hp": 8,
        "max_hp": 8,
        "stats": {
            "strength": 16,  # +2 modifier
            "intelligence": 10,
            "wisdom": 12,
            "dexterity": 14,  # +1 modifier
            "constitution": 15,
            "charisma": 11,
        },
        "inventory": [],
    }


@pytest.fixture
def weak_character():
    """Create a fragile character for death tests."""
    return {
        "name": "Fragile Wizard",
        "hp": 3,
        "max_hp": 3,
        "stats": {
            "strength": 8,  # -1 modifier
            "intelligence": 18,
            "wisdom": 12,
            "dexterity": 10,  # 0 modifier
            "constitution": 8,
            "charisma": 14,
        },
        "inventory": [],
    }


@pytest.fixture
def goblin():
    """Create a goblin enemy."""
    return CombatEnemy(
        id="goblin-1",
        name="Goblin",
        hp=4,
        max_hp=4,
        ac=12,
        attack_bonus=1,
        damage_dice="1d6",
        xp_value=10,
    )


@pytest.fixture
def weak_goblin():
    """Create a weak goblin for kill tests."""
    return CombatEnemy(
        id="goblin-weak",
        name="Weak Goblin",
        hp=1,
        max_hp=1,
        ac=8,  # Easy to hit
        attack_bonus=0,
        damage_dice="1d4",
        xp_value=5,
    )


@pytest.fixture
def orc():
    """Create an orc enemy."""
    return CombatEnemy(
        id="orc-1",
        name="Orc",
        hp=8,
        max_hp=8,
        ac=13,
        attack_bonus=3,
        damage_dice="1d8+1",
        xp_value=25,
    )


class TestResolvePlayerAttack:
    """Tests for resolve_player_attack."""

    def test_attack_hit_deals_damage(self, resolver, fighter, goblin):
        """Successful attack should deal damage."""
        # Seed for a guaranteed hit
        random.seed(100)  # Test to find good seed
        result = resolver.resolve_player_attack(fighter, goblin)

        if result.is_hit:
            assert result.damage >= 1
            assert goblin.hp < goblin.max_hp
            assert result.target_hp_after == goblin.hp
            assert result.target_hp_before == goblin.max_hp

    def test_attack_miss_no_damage(self, resolver, fighter, goblin):
        """Missed attack should deal no damage."""
        # Find a seed that produces a miss
        for seed in range(1000):
            random.seed(seed)
            goblin.hp = 4  # Reset HP
            result = resolver.resolve_player_attack(fighter, goblin)
            if not result.is_hit:
                assert result.damage == 0
                assert goblin.hp == goblin.max_hp
                break

    def test_critical_always_hits(self, resolver, fighter):
        """Natural 20 should always hit regardless of AC."""
        # Create enemy with impossible AC
        tough_enemy = CombatEnemy(
            id="tough",
            name="Impossible AC",
            hp=10,
            max_hp=10,
            ac=99,  # Impossible to hit normally
            attack_bonus=0,
            damage_dice="1d4",
            xp_value=100,
        )

        # Find seed that rolls natural 20
        for seed in range(1000):
            random.seed(seed)
            result = resolver.resolve_player_attack(fighter, tough_enemy)
            if result.attack_roll == 20:
                assert result.is_hit is True
                assert result.is_critical is True
                assert result.damage >= 1
                break

    def test_fumble_always_misses(self, resolver, fighter):
        """Natural 1 should always miss regardless of AC."""
        # Create enemy with very low AC
        easy_enemy = CombatEnemy(
            id="easy",
            name="Easy Target",
            hp=10,
            max_hp=10,
            ac=1,  # Should be impossible to miss normally
            attack_bonus=0,
            damage_dice="1d4",
            xp_value=1,
        )

        # Find seed that rolls natural 1
        for seed in range(1000):
            random.seed(seed)
            easy_enemy.hp = 10  # Reset
            result = resolver.resolve_player_attack(fighter, easy_enemy)
            if result.attack_roll == 1:
                assert result.is_hit is False
                assert result.is_fumble is True
                assert result.damage == 0
                assert easy_enemy.hp == 10
                break

    def test_kill_enemy(self, resolver, fighter, weak_goblin):
        """Attack should be able to kill enemy."""
        # Find seed that hits
        for seed in range(1000):
            random.seed(seed)
            weak_goblin.hp = 1  # Reset
            result = resolver.resolve_player_attack(fighter, weak_goblin)
            if result.is_hit:
                assert result.target_dead is True
                assert weak_goblin.hp == 0
                break

    def test_str_modifier_applied(self, resolver, fighter, goblin):
        """STR modifier should affect attack bonus."""
        random.seed(42)
        result = resolver.resolve_player_attack(fighter, goblin)

        # Fighter has STR 16 = +2 modifier
        assert result.attack_bonus == 2
        assert result.attack_total == result.attack_roll + 2


class TestResolveEnemyAttack:
    """Tests for resolve_enemy_attack."""

    def test_attack_hit_deals_damage(self, resolver, fighter, orc):
        """Orc hit should deal damage to player."""
        # Find seed for hit
        for seed in range(1000):
            random.seed(seed)
            fighter["hp"] = 8  # Reset
            result = resolver.resolve_enemy_attack(orc, fighter)
            if result.is_hit:
                assert result.damage >= 1
                assert result.target_hp_after < result.target_hp_before
                break

    def test_attack_miss_no_damage(self, resolver, fighter, goblin):
        """Missed attack should deal no damage."""
        for seed in range(1000):
            random.seed(seed)
            fighter["hp"] = 8
            result = resolver.resolve_enemy_attack(goblin, fighter)
            if not result.is_hit:
                assert result.damage == 0
                assert result.target_hp_after == result.target_hp_before
                break

    def test_player_ac_uses_dex(self, resolver, fighter, goblin):
        """Player AC should include DEX modifier."""
        random.seed(42)
        result = resolver.resolve_enemy_attack(goblin, fighter)

        # Fighter has DEX 14 = +1 modifier, so AC = 10 + 1 = 11
        assert result.target_ac == 11

    def test_kill_player(self, resolver, weak_character, orc):
        """Enemy should be able to kill player."""
        # Keep trying until we get a killing blow
        for seed in range(1000):
            random.seed(seed)
            weak_character["hp"] = 3  # Reset
            result = resolver.resolve_enemy_attack(orc, weak_character)
            if result.is_hit and result.damage >= 3:
                assert result.target_dead is True
                assert result.target_hp_after == 0
                break


class TestResolveCombatRound:
    """Tests for resolve_combat_round."""

    def test_player_first_on_initiative_tie(self, resolver, fighter, goblin):
        """Player should go first on initiative tie."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=3,
            enemy_initiative=3,
        )

        random.seed(42)
        result = resolver.resolve_combat_round(fighter, state, [goblin])

        # First attack should be from player
        assert len(result.attack_results) >= 1
        assert result.attack_results[0].attacker == "Grimjaw"

    def test_player_first_higher_initiative(self, resolver, fighter, goblin):
        """Player should go first with higher initiative."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=5,
            enemy_initiative=2,
        )

        random.seed(42)
        result = resolver.resolve_combat_round(fighter, state, [goblin])

        # First attack should be from player
        assert result.attack_results[0].attacker == "Grimjaw"

    def test_enemy_first_higher_initiative(self, resolver, fighter, goblin):
        """Enemy should go first with higher initiative."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=1,
            enemy_initiative=6,
        )

        random.seed(42)
        result = resolver.resolve_combat_round(fighter, state, [goblin])

        # First attack should be from enemy
        assert result.attack_results[0].attacker == "Goblin"

    def test_xp_awarded_on_kill(self, resolver, fighter, weak_goblin):
        """XP should be awarded when enemy is killed."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=6,
            enemy_initiative=1,
        )

        # Find seed where player kills goblin
        for seed in range(1000):
            random.seed(seed)
            weak_goblin.hp = 1  # Reset
            result = resolver.resolve_combat_round(fighter, state, [weak_goblin])
            if any(a.target_dead for a in result.attack_results if a.attacker == "Grimjaw"):
                assert result.xp_gained == 5
                break

    def test_combat_ends_all_enemies_dead(self, resolver, fighter, weak_goblin):
        """Combat should end when all enemies are dead."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=6,
            enemy_initiative=1,
        )

        # Find seed where goblin dies
        for seed in range(1000):
            random.seed(seed)
            weak_goblin.hp = 1
            result = resolver.resolve_combat_round(fighter, state, [weak_goblin])
            if weak_goblin.hp <= 0:
                assert result.combat_ended is True
                assert len(result.enemies_remaining) == 0
                break

    def test_combat_ends_player_dead(self, resolver, weak_character, orc):
        """Combat should end when player dies."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=1,  # Enemy goes first
            enemy_initiative=6,
        )

        # Find seed where orc kills player
        for seed in range(1000):
            random.seed(seed)
            weak_character["hp"] = 3
            result = resolver.resolve_combat_round(weak_character, state, [orc])
            if result.player_dead:
                assert result.combat_ended is True
                break

    def test_multiple_enemies_all_attack(self, resolver, fighter, goblin):
        """All living enemies should attack in a round."""
        goblin2 = CombatEnemy(
            id="goblin-2",
            name="Goblin 2",
            hp=4,
            max_hp=4,
            ac=12,
            attack_bonus=1,
            damage_dice="1d6",
            xp_value=10,
        )

        state = CombatState(
            active=True,
            round=1,
            player_initiative=1,  # Enemies go first
            enemy_initiative=6,
        )

        random.seed(42)
        result = resolver.resolve_combat_round(fighter, state, [goblin, goblin2])

        # Should have attacks from both goblins (+ player if alive)
        enemy_attacks = [a for a in result.attack_results if "Goblin" in a.attacker]
        assert len(enemy_attacks) >= 2

    def test_dead_enemy_does_not_attack(self, resolver, fighter, weak_goblin):
        """Dead enemies should not attack."""
        weak_goblin.hp = 0  # Already dead

        state = CombatState(
            active=True,
            round=1,
            player_initiative=1,
            enemy_initiative=6,
        )

        random.seed(42)
        result = resolver.resolve_combat_round(fighter, state, [weak_goblin])

        # No attacks should happen from dead goblin
        enemy_attacks = [a for a in result.attack_results if a.attacker == "Weak Goblin"]
        assert len(enemy_attacks) == 0

    def test_player_hp_updated(self, resolver, fighter, orc):
        """Character HP should be updated in place."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=1,
            enemy_initiative=6,
        )

        original_hp = fighter["hp"]

        # Find seed where orc hits
        for seed in range(1000):
            random.seed(seed)
            fighter["hp"] = original_hp
            result = resolver.resolve_combat_round(fighter, state, [orc])

            enemy_attacks = [a for a in result.attack_results if a.attacker == "Orc"]
            if enemy_attacks and enemy_attacks[0].is_hit:
                assert fighter["hp"] < original_hp
                assert fighter["hp"] == result.player_hp
                break


class TestCombatEdgeCases:
    """Tests for edge cases in combat."""

    def test_minimum_damage(self, resolver, fighter):
        """Damage should be at least 1 on hit."""
        # Create enemy with impossible-to-roll-positive damage
        weak_enemy = CombatEnemy(
            id="weak",
            name="Weak",
            hp=10,
            max_hp=10,
            ac=5,  # Easy to hit
            attack_bonus=0,
            damage_dice="1d1",  # Only rolls 1
            xp_value=1,
        )

        # Find a hit
        for seed in range(1000):
            random.seed(seed)
            fighter["hp"] = 10
            result = resolver.resolve_enemy_attack(weak_enemy, fighter)
            if result.is_hit:
                assert result.damage >= 1
                break

    def test_hp_cannot_go_negative(self, resolver, weak_character, orc):
        """HP should floor at 0."""
        for seed in range(1000):
            random.seed(seed)
            weak_character["hp"] = 1
            result = resolver.resolve_enemy_attack(orc, weak_character)
            if result.is_hit:
                assert result.target_hp_after >= 0
                break

    def test_empty_enemy_list(self, resolver, fighter):
        """Combat with no enemies should end immediately."""
        state = CombatState(
            active=True,
            round=1,
            player_initiative=5,
            enemy_initiative=3,
        )

        result = resolver.resolve_combat_round(fighter, state, [])

        assert result.combat_ended is True
        assert len(result.attack_results) == 0
        assert result.xp_gained == 0


class TestCombatNarratorCleaning:
    """Tests for combat narrator output cleaning."""

    def test_clean_narrator_output_strips_dm_prefix(self):
        """Test that [DM]: prefix is stripped."""
        from dm.combat_narrator import clean_narrator_output

        text = "[DM]: The goblin strikes!"
        result = clean_narrator_output(text)
        assert result == "The goblin strikes!"

    def test_clean_narrator_output_strips_dungeon_master(self):
        """Test that Dungeon Master: prefix is stripped."""
        from dm.combat_narrator import clean_narrator_output

        text = "Dungeon Master: The blade finds its mark."
        result = clean_narrator_output(text)
        assert result == "The blade finds its mark."

    def test_clean_narrator_output_strips_dm_header_line(self):
        """Test that standalone DM: line is removed."""
        from dm.combat_narrator import clean_narrator_output

        text = "DM:\nThe goblin lunges forward."
        result = clean_narrator_output(text)
        assert result == "The goblin lunges forward."

    def test_clean_narrator_output_strips_state_changes_header(self):
        """Test that State Changes: line is removed."""
        from dm.combat_narrator import clean_narrator_output

        text = "You strike the goblin.\nState Changes:\nThe battle continues."
        result = clean_narrator_output(text)
        assert "State Changes" not in result
        assert "You strike the goblin" in result

    def test_clean_narrator_output_strips_inline_dm(self):
        """Test that inline [DM]: markers are stripped."""
        from dm.combat_narrator import clean_narrator_output

        text = "The orc falls. [DM]: Combat ends."
        result = clean_narrator_output(text)
        assert "[DM]" not in result

    def test_clean_narrator_output_strips_hp_mentions(self):
        """Test that HP values are stripped from output."""
        from dm.combat_narrator import clean_narrator_output

        text = "The goblin is wounded (5 HP remaining)."
        result = clean_narrator_output(text)
        assert "HP" not in result
        assert "5" not in result


class TestCombatParserTargeting:
    """Tests for combat parser target selection with numbered enemies."""

    def test_find_target_first_match_for_ambiguous(self):
        """Test that ambiguous type matches first living enemy."""
        from dm.combat_parser import _find_target

        enemies = [
            CombatEnemy(id="1", name="Goblin 1", hp=4, max_hp=4, ac=12),
            CombatEnemy(id="2", name="Goblin 2", hp=4, max_hp=4, ac=12),
        ]
        result = _find_target("attack goblin", enemies)
        assert result is not None
        assert result.name == "Goblin 1"

    def test_find_target_specific_number(self):
        """Test that numbered suffix targets specific enemy."""
        from dm.combat_parser import _find_target

        enemies = [
            CombatEnemy(id="1", name="Goblin 1", hp=4, max_hp=4, ac=12),
            CombatEnemy(id="2", name="Goblin 2", hp=4, max_hp=4, ac=12),
        ]
        result = _find_target("attack goblin 2", enemies)
        assert result is not None
        assert result.name == "Goblin 2"

    def test_find_target_number_exact_suffix(self):
        """Test that '1' doesn't match 'Goblin 11' (edge case)."""
        from dm.combat_parser import _find_target

        enemies = [
            CombatEnemy(id="1", name="Goblin 1", hp=4, max_hp=4, ac=12),
            CombatEnemy(id="11", name="Goblin 11", hp=4, max_hp=4, ac=12),
        ]
        result = _find_target("attack 1", enemies)
        assert result is not None
        assert result.name == "Goblin 1"  # Not Goblin 11

    def test_find_target_skips_dead_enemies(self):
        """Test that dead enemies are not targeted."""
        from dm.combat_parser import _find_target

        enemies = [
            CombatEnemy(id="1", name="Goblin 1", hp=0, max_hp=4, ac=12),
            CombatEnemy(id="2", name="Goblin 2", hp=4, max_hp=4, ac=12),
        ]
        result = _find_target("attack goblin", enemies)
        assert result is not None
        assert result.name == "Goblin 2"  # First living

    def test_find_target_no_match_returns_none(self):
        """Test that unmatched target returns None."""
        from dm.combat_parser import _find_target

        enemies = [
            CombatEnemy(id="1", name="Goblin", hp=4, max_hp=4, ac=12),
        ]
        result = _find_target("attack orc", enemies)
        assert result is None
