"""Tests for BECMI rules module."""

from shared.becmi import (
    HIT_DICE,
    STARTING_ABILITIES,
    CharacterClass,
    get_hit_dice,
    get_starting_abilities,
    roll_starting_gold,
    roll_starting_hp,
)


class TestCharacterClass:
    """Tests for CharacterClass enum."""

    def test_fighter_value(self):
        assert CharacterClass.FIGHTER.value == "fighter"

    def test_thief_value(self):
        assert CharacterClass.THIEF.value == "thief"

    def test_magic_user_value(self):
        assert CharacterClass.MAGIC_USER.value == "magic_user"

    def test_cleric_value(self):
        assert CharacterClass.CLERIC.value == "cleric"

    def test_all_classes_in_hit_dice(self):
        """All classes should have hit dice defined."""
        for char_class in CharacterClass:
            assert char_class in HIT_DICE

    def test_all_classes_in_starting_abilities(self):
        """All classes should have starting abilities defined."""
        for char_class in CharacterClass:
            assert char_class in STARTING_ABILITIES


class TestHitDice:
    """Tests for hit dice by class."""

    def test_fighter_has_d8(self):
        assert get_hit_dice(CharacterClass.FIGHTER) == 8

    def test_cleric_has_d6(self):
        assert get_hit_dice(CharacterClass.CLERIC) == 6

    def test_thief_has_d4(self):
        assert get_hit_dice(CharacterClass.THIEF) == 4

    def test_magic_user_has_d4(self):
        assert get_hit_dice(CharacterClass.MAGIC_USER) == 4


class TestStartingAbilities:
    """Tests for starting abilities by class."""

    def test_fighter_abilities(self):
        abilities = get_starting_abilities(CharacterClass.FIGHTER)
        assert "Attack" in abilities
        assert "Parry" in abilities
        assert len(abilities) == 2

    def test_thief_abilities(self):
        abilities = get_starting_abilities(CharacterClass.THIEF)
        assert "Attack" in abilities
        assert "Backstab" in abilities
        assert "Pick Locks" in abilities
        assert "Hide in Shadows" in abilities
        assert len(abilities) == 4

    def test_magic_user_abilities(self):
        abilities = get_starting_abilities(CharacterClass.MAGIC_USER)
        assert "Attack" in abilities
        assert "Cast Spell" in abilities
        assert len(abilities) == 2

    def test_cleric_abilities(self):
        abilities = get_starting_abilities(CharacterClass.CLERIC)
        assert "Attack" in abilities
        assert "Turn Undead" in abilities
        assert len(abilities) == 2

    def test_abilities_are_copied(self):
        """Ensure we get a copy, not the original list."""
        abilities1 = get_starting_abilities(CharacterClass.FIGHTER)
        abilities2 = get_starting_abilities(CharacterClass.FIGHTER)
        abilities1.append("Test")
        assert "Test" not in abilities2

    def test_all_classes_have_attack(self):
        """All classes should have Attack ability."""
        for char_class in CharacterClass:
            abilities = get_starting_abilities(char_class)
            assert "Attack" in abilities


class TestRollStartingHp:
    """Tests for HP rolling."""

    def test_hp_minimum_is_one(self):
        """Even with -3 CON modifier, minimum HP is 1."""
        # Run multiple times to catch edge cases
        for _ in range(100):
            hp = roll_starting_hp(4, -3)  # d4 - 3, could be negative
            assert hp >= 1

    def test_hp_with_positive_modifier(self):
        """HP should include positive CON modifier."""
        # With +3 modifier, d4 should give 4-7
        results = [roll_starting_hp(4, 3) for _ in range(100)]
        assert min(results) >= 4
        assert max(results) <= 7

    def test_hp_with_zero_modifier(self):
        """HP with no modifier should be 1-die_size."""
        results = [roll_starting_hp(8, 0) for _ in range(100)]
        assert min(results) >= 1
        assert max(results) <= 8

    def test_hp_with_d8(self):
        """Fighter d8 HP range check."""
        results = [roll_starting_hp(8, 0) for _ in range(100)]
        assert all(1 <= hp <= 8 for hp in results)

    def test_hp_with_d6(self):
        """Cleric d6 HP range check."""
        results = [roll_starting_hp(6, 0) for _ in range(100)]
        assert all(1 <= hp <= 6 for hp in results)

    def test_hp_with_d4(self):
        """Thief/Magic-User d4 HP range check."""
        results = [roll_starting_hp(4, 0) for _ in range(100)]
        assert all(1 <= hp <= 4 for hp in results)


class TestRollStartingGold:
    """Tests for starting gold rolling."""

    def test_gold_minimum(self):
        """Starting gold should be at least 30 (3×1×10)."""
        for _ in range(100):
            gold = roll_starting_gold()
            assert gold >= 30

    def test_gold_maximum(self):
        """Starting gold should be at most 180 (3×6×10)."""
        for _ in range(100):
            gold = roll_starting_gold()
            assert gold <= 180

    def test_gold_is_multiple_of_ten(self):
        """Starting gold should always be a multiple of 10."""
        for _ in range(100):
            gold = roll_starting_gold()
            assert gold % 10 == 0

    def test_gold_range(self):
        """Starting gold should be 3d6 × 10 = 30-180."""
        for _ in range(100):
            gold = roll_starting_gold()
            assert 30 <= gold <= 180
            assert gold % 10 == 0
