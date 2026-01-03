"""Tests for dice rolling module."""

import random

import pytest

from shared.dice import roll, roll_attack, roll_initiative, roll_save


class TestRoll:
    """Tests for the roll function."""

    def test_roll_basic_d20(self):
        """Roll 1d20 should return value between 1 and 20."""
        random.seed(42)
        total, rolls = roll("1d20")

        assert len(rolls) == 1
        assert 1 <= rolls[0] <= 20
        assert total == rolls[0]

    def test_roll_multiple_dice(self):
        """Roll 3d6 should return three values between 1 and 6."""
        random.seed(42)
        total, rolls = roll("3d6")

        assert len(rolls) == 3
        assert all(1 <= r <= 6 for r in rolls)
        assert total == sum(rolls)

    def test_roll_with_positive_modifier(self):
        """Roll 2d6+3 should add modifier to total."""
        random.seed(42)
        total, rolls = roll("2d6+3")

        assert len(rolls) == 2
        assert total == sum(rolls) + 3

    def test_roll_with_negative_modifier(self):
        """Roll 1d8-1 should subtract modifier from total."""
        random.seed(42)
        total, rolls = roll("1d8-1")

        assert len(rolls) == 1
        assert total == rolls[0] - 1

    def test_roll_case_insensitive(self):
        """Roll should be case insensitive."""
        random.seed(42)
        total1, _ = roll("1D20")

        random.seed(42)
        total2, _ = roll("1d20")

        assert total1 == total2

    def test_roll_ignores_spaces(self):
        """Roll should ignore spaces."""
        random.seed(42)
        total1, _ = roll("2d6 + 3")

        random.seed(42)
        total2, _ = roll("2d6+3")

        assert total1 == total2

    def test_roll_invalid_notation_raises(self):
        """Invalid notation should raise ValueError."""
        with pytest.raises(ValueError):
            roll("invalid")

        with pytest.raises(ValueError):
            roll("d20")  # Missing number of dice

        with pytest.raises(ValueError):
            roll("2d")  # Missing die size

        with pytest.raises(ValueError):
            roll("")  # Empty string

        with pytest.raises(ValueError):
            roll(None)  # None

    def test_roll_distribution(self):
        """Roll should produce values within expected range over many rolls."""
        random.seed(42)
        min_seen = 100
        max_seen = 0

        for _ in range(1000):
            total, _ = roll("1d20")
            min_seen = min(min_seen, total)
            max_seen = max(max_seen, total)

        # Should see full range with 1000 rolls
        assert min_seen == 1
        assert max_seen == 20

    def test_roll_modifier_can_produce_negative(self):
        """Roll with negative modifier can produce negative totals."""
        # Force a roll of 1 by seeding
        random.seed(0)
        for _ in range(100):
            total, rolls = roll("1d4-5")
            if rolls[0] == 1:
                assert total == -4
                break

    def test_roll_large_dice(self):
        """Roll should handle large dice."""
        random.seed(42)
        total, rolls = roll("1d100")

        assert len(rolls) == 1
        assert 1 <= rolls[0] <= 100
        assert total == rolls[0]


class TestRollAttack:
    """Tests for roll_attack function."""

    def test_roll_attack_basic(self):
        """Roll attack should return d20 result."""
        random.seed(42)
        total, natural = roll_attack()

        assert 1 <= natural <= 20
        assert total == natural

    def test_roll_attack_with_bonus(self):
        """Roll attack should add bonus to total."""
        random.seed(42)
        total, natural = roll_attack(5)

        assert 1 <= natural <= 20
        assert total == natural + 5

    def test_roll_attack_with_negative_bonus(self):
        """Roll attack should handle negative bonus."""
        random.seed(42)
        total, natural = roll_attack(-2)

        assert total == natural - 2

    def test_roll_attack_critical(self):
        """Should be able to roll natural 20."""
        # Roll many times to ensure we can get a 20
        random.seed(42)
        found_20 = False
        for _ in range(1000):
            _, natural = roll_attack()
            if natural == 20:
                found_20 = True
                break

        assert found_20, "Should be able to roll natural 20"

    def test_roll_attack_fumble(self):
        """Should be able to roll natural 1."""
        # Roll many times to ensure we can get a 1
        random.seed(42)
        found_1 = False
        for _ in range(1000):
            _, natural = roll_attack()
            if natural == 1:
                found_1 = True
                break

        assert found_1, "Should be able to roll natural 1"


class TestRollInitiative:
    """Tests for roll_initiative function."""

    def test_roll_initiative_range(self):
        """Initiative should be 1-6."""
        random.seed(42)
        results = [roll_initiative() for _ in range(100)]

        assert all(1 <= r <= 6 for r in results)

    def test_roll_initiative_distribution(self):
        """Initiative should cover full range."""
        random.seed(42)
        results = set()
        for _ in range(1000):
            results.add(roll_initiative())

        assert results == {1, 2, 3, 4, 5, 6}


class TestRollSave:
    """Tests for roll_save function."""

    def test_roll_save_success(self):
        """Save should succeed when roll >= target."""
        # Seed to get a high roll
        random.seed(42)
        for _ in range(100):
            success, total = roll_save(10)
            if total >= 10:
                assert success is True
                break

    def test_roll_save_failure(self):
        """Save should fail when roll < target."""
        # Seed to get a low roll
        random.seed(42)
        for _ in range(100):
            success, total = roll_save(15)
            if total < 15:
                assert success is False
                break

    def test_roll_save_with_modifier(self):
        """Save should apply modifier."""
        random.seed(42)
        success, total = roll_save(10, modifier=5)

        # Total includes the +5 modifier
        assert total >= 6  # Minimum roll of 1 + 5
