"""Tests for item catalog and inventory helpers."""

import pytest

from shared.items import (
    ITEM_CATALOG,
    STARTING_EQUIPMENT,
    ItemType,
    find_item_by_name,
    get_starting_equipment,
)


class TestStartingEquipment:
    """Tests for starting equipment by class."""

    def test_starting_equipment_fighter(self) -> None:
        """Fighter gets sword, shield, chain mail, backpack, rations, torch."""
        equipment = get_starting_equipment("fighter")
        item_ids = [item["item_id"] for item in equipment]

        assert "sword" in item_ids
        assert "shield" in item_ids
        assert "chain_mail" in item_ids
        assert "backpack" in item_ids
        assert "rations" in item_ids
        assert "torch" in item_ids

    def test_starting_equipment_thief(self) -> None:
        """Thief gets dagger, leather armor, thieves' tools, backpack, rations, torch."""
        equipment = get_starting_equipment("thief")
        item_ids = [item["item_id"] for item in equipment]

        assert "dagger" in item_ids
        assert "leather_armor" in item_ids
        assert "thieves_tools" in item_ids
        assert "backpack" in item_ids
        assert "rations" in item_ids
        assert "torch" in item_ids

    def test_starting_equipment_cleric(self) -> None:
        """Cleric gets mace, shield, chain mail, holy symbol, backpack, rations."""
        equipment = get_starting_equipment("cleric")
        item_ids = [item["item_id"] for item in equipment]

        assert "mace" in item_ids
        assert "shield" in item_ids
        assert "chain_mail" in item_ids
        assert "holy_symbol" in item_ids
        assert "backpack" in item_ids
        assert "rations" in item_ids

    def test_starting_equipment_magic_user(self) -> None:
        """Magic user gets dagger, staff, spellbook, robes, backpack, rations."""
        equipment = get_starting_equipment("magic_user")
        item_ids = [item["item_id"] for item in equipment]

        assert "dagger" in item_ids
        assert "staff" in item_ids
        assert "spellbook" in item_ids
        assert "robes" in item_ids
        assert "backpack" in item_ids
        assert "rations" in item_ids

    def test_starting_equipment_structure(self) -> None:
        """Equipment items have correct structure."""
        equipment = get_starting_equipment("fighter")

        for item in equipment:
            assert "item_id" in item
            assert "name" in item
            assert "quantity" in item
            assert "item_type" in item
            assert "description" in item
            assert item["quantity"] == 1

    def test_starting_equipment_unknown_class(self) -> None:
        """Unknown class returns empty list."""
        equipment = get_starting_equipment("bard")
        assert equipment == []

    def test_starting_equipment_case_insensitive(self) -> None:
        """Class lookup is case insensitive."""
        equipment = get_starting_equipment("FIGHTER")
        assert len(equipment) > 0


class TestFindItemByName:
    """Tests for find_item_by_name function."""

    def test_exact_match_by_name(self) -> None:
        """Exact match on item name works."""
        item = find_item_by_name("Sword")
        assert item is not None
        assert item.id == "sword"

    def test_exact_match_case_insensitive(self) -> None:
        """Match is case insensitive."""
        item = find_item_by_name("SWORD")
        assert item is not None
        assert item.id == "sword"

    def test_exact_match_by_id(self) -> None:
        """Exact match on item ID works."""
        item = find_item_by_name("potion_healing")
        assert item is not None
        assert item.name == "Potion of Healing"

    def test_partial_match(self) -> None:
        """Partial match on name works."""
        item = find_item_by_name("healing")
        assert item is not None
        assert item.id == "potion_healing"

    def test_alias_match(self) -> None:
        """Alias lookup works."""
        # "red potion" is an alias for potion_healing
        item = find_item_by_name("red potion")
        assert item is not None
        assert item.id == "potion_healing"

    def test_alias_healing_potion(self) -> None:
        """'healing potion' finds potion_healing."""
        item = find_item_by_name("healing potion")
        assert item is not None
        assert item.id == "potion_healing"

    def test_alias_key(self) -> None:
        """'key' finds rusty_key."""
        item = find_item_by_name("key")
        assert item is not None
        assert item.id == "rusty_key"

    def test_dynamic_quest_item_locket(self) -> None:
        """Dynamic quest item created for 'ornate locket'."""
        item = find_item_by_name("ornate locket")
        assert item is not None
        assert item.item_type == ItemType.QUEST
        assert item.id.startswith("quest_")
        assert "ornate_locket" in item.id
        assert item.name == "Ornate Locket"

    def test_dynamic_quest_item_letter(self) -> None:
        """Dynamic quest item created for 'bloody letter'."""
        item = find_item_by_name("bloody letter")
        assert item is not None
        assert item.item_type == ItemType.QUEST
        assert "Bloody Letter" == item.name

    def test_unknown_item_returns_none(self) -> None:
        """Unknown item with no quest keyword returns None."""
        item = find_item_by_name("Vorpal Blade")
        assert item is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        item = find_item_by_name("")
        assert item is None

    def test_whitespace_only_returns_none(self) -> None:
        """Whitespace only returns None."""
        item = find_item_by_name("   ")
        assert item is None

    def test_weapon_has_damage_dice(self) -> None:
        """Weapons have damage dice defined."""
        item = find_item_by_name("sword")
        assert item is not None
        assert item.damage_dice == "1d8"

    def test_armor_has_ac_bonus(self) -> None:
        """Armor has AC bonus defined."""
        item = find_item_by_name("chain mail")
        assert item is not None
        assert item.ac_bonus == 4

    def test_consumable_has_healing(self) -> None:
        """Healing potions have healing defined."""
        item = find_item_by_name("potion of healing")
        assert item is not None
        assert item.healing > 0


class TestItemCatalog:
    """Tests for the item catalog."""

    def test_all_classes_have_starting_equipment(self) -> None:
        """All 4 character classes have starting equipment defined."""
        assert "fighter" in STARTING_EQUIPMENT
        assert "thief" in STARTING_EQUIPMENT
        assert "cleric" in STARTING_EQUIPMENT
        assert "magic_user" in STARTING_EQUIPMENT

    def test_starting_equipment_items_exist(self) -> None:
        """All starting equipment items exist in catalog."""
        for character_class, items in STARTING_EQUIPMENT.items():
            for item_id in items:
                assert item_id in ITEM_CATALOG, f"{item_id} missing for {character_class}"

    def test_catalog_has_basic_weapons(self) -> None:
        """Catalog has basic weapons."""
        assert "sword" in ITEM_CATALOG
        assert "dagger" in ITEM_CATALOG
        assert "mace" in ITEM_CATALOG
        assert "staff" in ITEM_CATALOG

    def test_catalog_has_armor(self) -> None:
        """Catalog has armor items."""
        assert "chain_mail" in ITEM_CATALOG
        assert "leather_armor" in ITEM_CATALOG
        assert "shield" in ITEM_CATALOG
        assert "robes" in ITEM_CATALOG

    def test_catalog_has_consumables(self) -> None:
        """Catalog has consumable items."""
        assert "potion_healing" in ITEM_CATALOG
        assert "rations" in ITEM_CATALOG

    def test_catalog_has_misc_items(self) -> None:
        """Catalog has misc items."""
        assert "torch" in ITEM_CATALOG
        assert "backpack" in ITEM_CATALOG
        assert "thieves_tools" in ITEM_CATALOG
        assert "holy_symbol" in ITEM_CATALOG
        assert "spellbook" in ITEM_CATALOG
