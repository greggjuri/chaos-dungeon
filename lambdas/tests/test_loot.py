"""Tests for loot table system."""


from shared.loot import (
    LOOT_TABLES,
    get_loot_table,
    roll_combat_loot,
    roll_enemy_loot,
    weighted_random_choice,
)


class TestLootTables:
    """Test loot table definitions."""

    def test_all_bestiary_enemies_have_tables(self):
        """Verify all bestiary enemies have loot tables."""
        from dm.bestiary import BESTIARY

        for enemy_type in BESTIARY:
            # Normalize the same way the loot module does
            normalized = enemy_type.lower().strip().replace(" ", "_")
            table = get_loot_table(normalized)
            assert table is not None, f"Missing loot table for {enemy_type}"

    def test_unknown_enemy_fallback_exists(self):
        """Verify fallback table exists."""
        assert "unknown_enemy" in LOOT_TABLES

    def test_loot_table_structure(self):
        """Verify all tables have required fields."""
        for name, table in LOOT_TABLES.items():
            assert "gold_dice" in table, f"{name} missing gold_dice"
            assert "rolls" in table, f"{name} missing rolls"
            assert "items" in table, f"{name} missing items"
            assert isinstance(table["items"], list)

    def test_all_loot_items_exist_in_catalog(self):
        """Verify all items in loot tables exist in item catalog."""
        from shared.items import ITEM_CATALOG

        for table_name, table in LOOT_TABLES.items():
            for entry in table["items"]:
                item_id = entry["item"]
                if item_id is not None:
                    assert item_id in ITEM_CATALOG, (
                        f"Item '{item_id}' in loot table '{table_name}' "
                        f"not found in ITEM_CATALOG"
                    )


class TestWeightedChoice:
    """Test weighted random selection."""

    def test_weighted_choice_returns_item(self):
        """Weighted choice should return valid item."""
        items = [
            {"weight": 100, "item": "sword"},
        ]
        result = weighted_random_choice(items)
        assert result == "sword"

    def test_weighted_choice_can_return_none(self):
        """Weighted choice can return None for empty drops."""
        items = [
            {"weight": 100, "item": None},
        ]
        result = weighted_random_choice(items)
        assert result is None

    def test_weighted_choice_respects_weights(self):
        """Weighted choice should statistically favor higher weights."""
        # With 99% weight on sword, should almost always get sword
        items = [
            {"weight": 99, "item": "sword"},
            {"weight": 1, "item": "dagger"},
        ]
        results = [weighted_random_choice(items) for _ in range(100)]
        sword_count = results.count("sword")
        # Should get sword at least 90% of the time
        assert sword_count >= 90


class TestRollEnemyLoot:
    """Test single enemy loot rolling."""

    def test_roll_goblin_loot(self):
        """Roll loot for known enemy type."""
        result = roll_enemy_loot("goblin")
        assert "gold" in result
        assert "items" in result
        assert isinstance(result["gold"], int)
        assert isinstance(result["items"], list)

    def test_roll_unknown_enemy_loot(self):
        """Unknown enemies use fallback table."""
        result = roll_enemy_loot("ancient_wyrm")
        assert "gold" in result
        assert result["gold"] >= 0

    def test_roll_loot_gold_range(self):
        """Gold should be within dice range."""
        # Goblin uses 1d6, so gold should be 1-6
        results = [roll_enemy_loot("goblin")["gold"] for _ in range(50)]
        assert all(1 <= g <= 6 for g in results)

    def test_roll_wolf_no_gold(self):
        """Wolf table has 0d0 gold - should always be 0."""
        results = [roll_enemy_loot("wolf")["gold"] for _ in range(10)]
        assert all(g == 0 for g in results)

    def test_case_insensitive_lookup(self):
        """Lookup should be case insensitive."""
        result1 = roll_enemy_loot("Goblin")
        result2 = roll_enemy_loot("GOBLIN")
        result3 = roll_enemy_loot("goblin")
        # All should succeed (gold >= 0)
        assert result1["gold"] >= 0
        assert result2["gold"] >= 0
        assert result3["gold"] >= 0

    def test_space_normalized_lookup(self):
        """Lookup should handle spaces in enemy names."""
        # "giant rat" in bestiary should match "giant_rat" loot table
        result = roll_enemy_loot("giant rat")
        assert "gold" in result
        assert result["gold"] >= 0


class TestRollCombatLoot:
    """Test combat loot rolling."""

    def test_roll_multiple_enemies(self):
        """Loot from multiple enemies combines."""
        enemies = [
            {"name": "Goblin 1"},
            {"name": "Goblin 2"},
        ]
        result = roll_combat_loot(enemies)
        assert "gold" in result
        assert "items" in result
        assert result["source"] == "combat_victory"

    def test_enemy_numbering_stripped(self):
        """Enemy numbers should be stripped for table lookup."""
        enemies = [{"name": "Skeleton 3"}]
        result = roll_combat_loot(enemies)
        # Should use skeleton table (1d4 gold = 1-4), not fail
        assert "gold" in result
        assert 1 <= result["gold"] <= 4

    def test_mixed_enemy_types(self):
        """Different enemy types combine loot correctly."""
        enemies = [
            {"name": "Goblin"},
            {"name": "Skeleton"},
        ]
        result = roll_combat_loot(enemies)
        # Gold should be sum of goblin (1d6) + skeleton (1d4) = 2-10
        assert 2 <= result["gold"] <= 10

    def test_empty_enemy_list(self):
        """Empty enemy list returns zero loot."""
        result = roll_combat_loot([])
        assert result["gold"] == 0
        assert result["items"] == []
        assert result["source"] == "combat_victory"


class TestGetLootTable:
    """Test loot table lookup."""

    def test_get_existing_table(self):
        """Get existing loot table."""
        table = get_loot_table("goblin")
        assert table is not None
        assert table["gold_dice"] == "1d6"

    def test_get_nonexistent_table(self):
        """Non-existent table returns None."""
        table = get_loot_table("nonexistent_monster")
        assert table is None

    def test_get_table_case_insensitive(self):
        """Table lookup is case insensitive."""
        table = get_loot_table("GOBLIN")
        assert table is not None
