"""Tests for bestiary module."""

import random

import pytest

from dm.bestiary import (
    BESTIARY,
    get_enemy_template,
    list_enemy_types,
    spawn_enemies,
    spawn_enemy,
)
from dm.models import CombatEnemy


class TestSpawnEnemy:
    """Tests for spawn_enemy function."""

    def test_spawn_goblin(self):
        """Goblin should spawn with correct stats."""
        random.seed(42)
        enemy = spawn_enemy("goblin")

        assert isinstance(enemy, CombatEnemy)
        assert enemy.name == "Goblin"
        assert enemy.ac == 12
        assert enemy.attack_bonus == 1
        assert enemy.damage_dice == "1d6"
        assert enemy.xp_value == 10
        assert 1 <= enemy.hp <= 6
        assert enemy.hp == enemy.max_hp

    def test_spawn_orc(self):
        """Orc should spawn with correct stats."""
        random.seed(42)
        enemy = spawn_enemy("orc")

        assert enemy.name == "Orc"
        assert enemy.ac == 13
        assert enemy.attack_bonus == 2
        assert enemy.damage_dice == "1d8"
        assert enemy.xp_value == 25
        # 1d8+1 = 2-9 HP
        assert 2 <= enemy.hp <= 9

    def test_spawn_vampire(self):
        """Vampire should spawn as a dangerous enemy."""
        random.seed(42)
        enemy = spawn_enemy("vampire")

        assert enemy.name == "Vampire"
        assert enemy.ac == 18
        assert enemy.attack_bonus == 8
        assert enemy.damage_dice == "1d10+4"
        assert enemy.xp_value == 1000
        # 8d8 = 8-64 HP
        assert 8 <= enemy.hp <= 64

    def test_spawn_case_insensitive(self):
        """Enemy type should be case-insensitive."""
        random.seed(42)
        enemy1 = spawn_enemy("GOBLIN")

        random.seed(42)
        enemy2 = spawn_enemy("goblin")

        assert enemy1.name == enemy2.name
        assert enemy1.hp == enemy2.hp

    def test_spawn_with_spaces(self):
        """Enemy type should handle leading/trailing spaces."""
        random.seed(42)
        enemy = spawn_enemy("  goblin  ")

        assert enemy.name == "Goblin"

    def test_spawn_multi_word_enemy(self):
        """Multi-word enemy types should work."""
        random.seed(42)
        enemy = spawn_enemy("giant spider")

        assert enemy.name == "Giant Spider"
        assert enemy.xp_value == 50

    def test_spawn_unknown_raises(self):
        """Unknown enemy type should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            spawn_enemy("unknown monster")

        assert "Unknown enemy type" in str(exc_info.value)

    def test_spawn_unique_ids(self):
        """Each spawned enemy should have unique ID."""
        enemies = [spawn_enemy("goblin") for _ in range(10)]
        ids = [e.id for e in enemies]

        assert len(ids) == len(set(ids)), "Enemy IDs should be unique"

    def test_spawn_hp_varies(self):
        """HP should vary across multiple spawns."""
        hp_values = set()
        for i in range(100):
            random.seed(i)  # Different seed each time
            enemy = spawn_enemy("goblin")
            hp_values.add(enemy.hp)

        # With 100 spawns of 1d6, we should see most values
        assert len(hp_values) >= 4, "HP should vary across spawns"

    def test_spawn_minimum_hp(self):
        """HP should never be less than 1."""
        # Try many times to ensure we never get 0 HP
        for i in range(100):
            random.seed(i)
            enemy = spawn_enemy("giant rat")  # 1d4, could theoretically roll low
            assert enemy.hp >= 1


class TestGetEnemyTemplate:
    """Tests for get_enemy_template function."""

    def test_get_existing_template(self):
        """Should return template for known enemy."""
        template = get_enemy_template("goblin")

        assert template is not None
        assert template["name"] == "Goblin"
        assert template["hp_dice"] == "1d6"

    def test_get_unknown_template(self):
        """Should return None for unknown enemy."""
        template = get_enemy_template("unicorn")

        assert template is None

    def test_get_template_case_insensitive(self):
        """Should be case-insensitive."""
        template = get_enemy_template("VAMPIRE")

        assert template is not None
        assert template["name"] == "Vampire"


class TestListEnemyTypes:
    """Tests for list_enemy_types function."""

    def test_list_returns_all(self):
        """Should return all enemy types."""
        types = list_enemy_types()

        assert len(types) == len(BESTIARY)
        assert "goblin" in types
        assert "vampire" in types
        assert "orc" in types

    def test_list_is_lowercase(self):
        """All types should be lowercase."""
        types = list_enemy_types()

        for t in types:
            assert t == t.lower()


class TestBestiaryCompleteness:
    """Tests for bestiary data integrity."""

    def test_all_enemies_have_required_fields(self):
        """All enemies should have required stat fields."""
        required = ["name", "hp_dice", "ac", "attack_bonus", "damage_dice", "xp_value"]

        for enemy_type, template in BESTIARY.items():
            for field in required:
                assert field in template, f"{enemy_type} missing {field}"

    def test_all_hp_dice_valid(self):
        """All HP dice should be valid notation."""
        for enemy_type, _template in BESTIARY.items():
            # Should not raise when spawning
            try:
                random.seed(42)
                enemy = spawn_enemy(enemy_type)
                assert enemy.hp >= 1
            except ValueError as e:
                pytest.fail(f"{enemy_type} has invalid hp_dice: {e}")

    def test_xp_values_positive(self):
        """All XP values should be positive."""
        for enemy_type, template in BESTIARY.items():
            assert template["xp_value"] > 0, f"{enemy_type} has invalid XP"

    def test_ac_values_reasonable(self):
        """AC values should be in reasonable range."""
        for enemy_type, template in BESTIARY.items():
            assert 10 <= template["ac"] <= 25, f"{enemy_type} has unusual AC"


class TestSpawnEnemies:
    """Tests for spawn_enemies function (batch spawning with numbering)."""

    def test_spawn_enemies_numbers_duplicates(self):
        """Test that duplicate enemy types get numbered names."""
        random.seed(42)
        enemies = spawn_enemies(["goblin", "goblin", "goblin"])
        names = [e.name for e in enemies]
        assert names == ["Goblin 1", "Goblin 2", "Goblin 3"]

    def test_spawn_enemies_no_number_for_singles(self):
        """Test that single enemy types don't get numbered."""
        random.seed(42)
        enemies = spawn_enemies(["goblin", "orc", "skeleton"])
        names = [e.name for e in enemies]
        assert names == ["Goblin", "Orc", "Skeleton"]

    def test_spawn_enemies_mixed_numbering(self):
        """Test mixed duplicates and singles."""
        random.seed(42)
        enemies = spawn_enemies(["goblin", "orc", "goblin"])
        names = [e.name for e in enemies]
        assert names == ["Goblin 1", "Orc", "Goblin 2"]

    def test_spawn_enemies_empty_list(self):
        """Empty list returns empty list."""
        enemies = spawn_enemies([])
        assert enemies == []

    def test_spawn_enemies_unique_ids(self):
        """All spawned enemies should have unique IDs."""
        enemies = spawn_enemies(["goblin", "goblin", "orc", "orc"])
        ids = [e.id for e in enemies]
        assert len(ids) == len(set(ids))

    def test_spawn_enemies_unknown_raises(self):
        """Unknown enemy type should raise ValueError."""
        with pytest.raises(ValueError):
            spawn_enemies(["goblin", "unknown_monster"])


class TestSpawnEnemyWithIndex:
    """Tests for spawn_enemy with index parameter."""

    def test_spawn_with_index(self):
        """Enemy should have numbered name when index provided."""
        random.seed(42)
        enemy = spawn_enemy("goblin", index=1)
        assert enemy.name == "Goblin 1"

    def test_spawn_without_index(self):
        """Enemy should have base name when no index."""
        random.seed(42)
        enemy = spawn_enemy("goblin")
        assert enemy.name == "Goblin"

    def test_spawn_with_various_indices(self):
        """Various indices should work correctly."""
        for i in [1, 2, 10, 99]:
            enemy = spawn_enemy("orc", index=i)
            assert enemy.name == f"Orc {i}"
