"""Tests for commerce system."""

from unittest.mock import MagicMock

import pytest

from dm.models import CommerceTransaction, StateChanges
from dm.service import DMService
from shared.actions import is_buy_action, is_sell_action


@pytest.fixture
def dm_service():
    """Create a DMService with a mock DB."""
    mock_db = MagicMock()
    return DMService(db=mock_db)


@pytest.fixture
def sample_character():
    """Create a sample character dict."""
    return {
        "character_id": "test-char-id",
        "user_id": "test-user-id",
        "name": "Test Hero",
        "character_class": "fighter",
        "level": 1,
        "xp": 0,
        "hp": 10,
        "max_hp": 10,
        "gold": 50,
        "inventory": [],
        "stats": {
            "strength": 14,
            "intelligence": 10,
            "wisdom": 10,
            "dexterity": 12,
            "constitution": 13,
            "charisma": 11,
        },
    }


class TestCommerceDetection:
    """Tests for buy/sell action detection."""

    @pytest.mark.parametrize("action", [
        "I want to sell my torch",
        "sell the dagger",
        "I'd like to pawn this ring",
        "trade my sword for gold",
        "exchange this amulet for gold",
        "Sell all my items",
        "I sell the shield to the merchant",
    ])
    def test_sell_patterns_detected(self, action):
        """Sell patterns are detected correctly."""
        assert is_sell_action(action) is True

    @pytest.mark.parametrize("action", [
        "I look around the shop",
        "I attack the merchant",
        "What do you have for sale?",
        "I look at the swords",
        "Tell me about your wares",
    ])
    def test_non_sell_not_detected(self, action):
        """Non-sell actions are not detected as sell."""
        assert is_sell_action(action) is False

    @pytest.mark.parametrize("action", [
        "I want to buy a sword",
        "purchase some rations",
        "I'll pay for a healing potion",
        "Buy me a torch",
        "I purchase the dagger",
        "I get a shield from the merchant",
    ])
    def test_buy_patterns_detected(self, action):
        """Buy patterns are detected correctly."""
        # NOTE: "acquire" was removed - too ambiguous
        assert is_buy_action(action) is True

    @pytest.mark.parametrize("action", [
        "I look at the swords",
        "What's the price?",
        "I leave the shop",
        "Show me your inventory",
        "I examine the armor",
    ])
    def test_non_buy_not_detected(self, action):
        """Non-buy actions are not detected as buy."""
        assert is_buy_action(action) is False


class TestCommerceModels:
    """Tests for commerce data models."""

    def test_commerce_transaction_valid(self):
        """Valid commerce transaction parses correctly."""
        tx = CommerceTransaction(item="sword", price=10)
        assert tx.item == "sword"
        assert tx.price == 10

    def test_commerce_transaction_zero_price(self):
        """Zero price is allowed (free items in some contexts)."""
        tx = CommerceTransaction(item="torch", price=0)
        assert tx.price == 0

    def test_commerce_transaction_price_validation(self):
        """Negative price is rejected."""
        with pytest.raises(ValueError):
            CommerceTransaction(item="sword", price=-5)

    def test_state_changes_with_commerce_sell(self):
        """StateChanges accepts commerce_sell field."""
        state = StateChanges(commerce_sell="torch")
        assert state.commerce_sell == "torch"
        assert state.commerce_buy is None

    def test_state_changes_with_commerce_buy(self):
        """StateChanges accepts commerce_buy field."""
        state = StateChanges(
            commerce_buy=CommerceTransaction(item="sword", price=10),
        )
        assert state.commerce_buy is not None
        assert state.commerce_buy.item == "sword"
        assert state.commerce_buy.price == 10

    def test_state_changes_with_both_commerce_fields(self):
        """StateChanges accepts both commerce fields simultaneously."""
        state = StateChanges(
            commerce_sell="torch",
            commerce_buy=CommerceTransaction(item="sword", price=10),
        )
        assert state.commerce_sell == "torch"
        assert state.commerce_buy.item == "sword"


class TestCommerceProcessing:
    """Tests for commerce transaction processing."""

    def test_sell_removes_item_adds_gold(self, dm_service, sample_character):
        """Selling item removes it and adds 50% value."""
        # Add sword (value=10) to inventory
        sample_character["inventory"] = [{
            "item_id": "sword",
            "name": "Sword",
            "quantity": 1,
            "item_type": "weapon",
            "description": "A trusty steel sword.",
        }]
        sample_character["gold"] = 0

        state = StateChanges(commerce_sell="sword")
        result = dm_service._process_commerce(sample_character, state)

        assert result["sold"] == {"item": "sword", "gold": 5}  # 10 / 2 = 5
        assert sample_character["gold"] == 5
        assert len(sample_character["inventory"]) == 0

    def test_sell_minimum_price_is_one(self, dm_service, sample_character):
        """Items worth less than 2 gold sell for 1 gold minimum."""
        # Add torch (value=1) to inventory
        sample_character["inventory"] = [{
            "item_id": "torch",
            "name": "Torch",
            "quantity": 1,
            "item_type": "misc",
            "description": "A torch",
        }]
        sample_character["gold"] = 0

        state = StateChanges(commerce_sell="torch")
        result = dm_service._process_commerce(sample_character, state)

        # torch value=1, 50%=0, min=1
        assert result["sold"]["gold"] == 1
        assert sample_character["gold"] == 1

    def test_sell_missing_item_fails(self, dm_service, sample_character):
        """Cannot sell item not in inventory."""
        sample_character["inventory"] = []

        state = StateChanges(commerce_sell="torch")
        result = dm_service._process_commerce(sample_character, state)

        assert result["error"] is not None
        assert "not in inventory" in result["error"]
        assert sample_character["gold"] == sample_character.get("gold", 0)

    def test_buy_deducts_gold_adds_item(self, dm_service, sample_character):
        """Buying item deducts gold and adds item."""
        sample_character["gold"] = 20
        sample_character["inventory"] = []

        state = StateChanges(
            commerce_buy=CommerceTransaction(item="sword", price=10)
        )
        result = dm_service._process_commerce(sample_character, state)

        assert result["bought"] == {"item": "sword", "gold": 10}
        assert sample_character["gold"] == 10
        assert len(sample_character["inventory"]) == 1
        assert sample_character["inventory"][0]["item_id"] == "sword"

    def test_buy_insufficient_gold_fails(self, dm_service, sample_character):
        """Cannot buy if not enough gold."""
        sample_character["gold"] = 5
        sample_character["inventory"] = []

        state = StateChanges(
            commerce_buy=CommerceTransaction(item="sword", price=10)
        )
        result = dm_service._process_commerce(sample_character, state)

        assert result["error"] is not None
        assert "Cannot afford" in result["error"]
        assert sample_character["gold"] == 5  # Unchanged
        assert len(sample_character["inventory"]) == 0

    def test_buy_unknown_item_fails(self, dm_service, sample_character):
        """Cannot buy item not in catalog."""
        sample_character["gold"] = 100
        sample_character["inventory"] = []

        state = StateChanges(
            commerce_buy=CommerceTransaction(item="magic_unobtainium", price=50)
        )
        result = dm_service._process_commerce(sample_character, state)

        assert result["error"] is not None
        assert "Unknown item" in result["error"]
        assert sample_character["gold"] == 100  # Unchanged

    def test_buy_stacks_existing_item(self, dm_service, sample_character):
        """Buying item already owned increases quantity."""
        sample_character["gold"] = 20
        sample_character["inventory"] = [{
            "item_id": "torch",
            "name": "Torch",
            "quantity": 3,
            "item_type": "misc",
            "description": "A torch",
        }]

        state = StateChanges(
            commerce_buy=CommerceTransaction(item="torch", price=1)
        )
        result = dm_service._process_commerce(sample_character, state)

        assert result["bought"]["item"] == "torch"
        assert len(sample_character["inventory"]) == 1
        assert sample_character["inventory"][0]["quantity"] == 4
        assert sample_character["gold"] == 19

    def test_sell_decrements_quantity(self, dm_service, sample_character):
        """Selling stacked item decrements quantity."""
        sample_character["inventory"] = [{
            "item_id": "torch",
            "name": "Torch",
            "quantity": 5,
            "item_type": "misc",
            "description": "A torch",
        }]
        sample_character["gold"] = 0

        state = StateChanges(commerce_sell="torch")
        result = dm_service._process_commerce(sample_character, state)

        assert result["sold"]["item"] == "torch"
        assert len(sample_character["inventory"]) == 1
        assert sample_character["inventory"][0]["quantity"] == 4

    def test_sell_by_alias(self, dm_service, sample_character):
        """Can sell item using alias name."""
        sample_character["inventory"] = [{
            "item_id": "potion_healing",
            "name": "Potion of Healing",
            "quantity": 1,
            "item_type": "consumable",
            "description": "A healing potion",
        }]
        sample_character["gold"] = 0

        # Sell using alias "healing potion" (maps to potion_healing)
        state = StateChanges(commerce_sell="healing potion")
        result = dm_service._process_commerce(sample_character, state)

        assert result["sold"] is not None
        assert len(sample_character["inventory"]) == 0

    def test_no_commerce_returns_empty_result(self, dm_service, sample_character):
        """No commerce fields returns empty result."""
        state = StateChanges()
        result = dm_service._process_commerce(sample_character, state)

        assert result["sold"] is None
        assert result["bought"] is None
        assert result["error"] is None


class TestNormalizeItemId:
    """Tests for item ID normalization."""

    def test_direct_catalog_match(self, dm_service):
        """Direct catalog ID matches."""
        assert dm_service._normalize_item_id("sword") == "sword"
        assert dm_service._normalize_item_id("torch") == "torch"

    def test_space_to_underscore(self, dm_service):
        """Spaces converted to underscores."""
        assert dm_service._normalize_item_id("chain mail") == "chain_mail"
        assert dm_service._normalize_item_id("leather armor") == "leather_armor"

    def test_case_insensitive(self, dm_service):
        """Matching is case-insensitive."""
        assert dm_service._normalize_item_id("SWORD") == "sword"
        assert dm_service._normalize_item_id("Chain Mail") == "chain_mail"

    def test_alias_lookup(self, dm_service):
        """Aliases resolve to catalog items."""
        assert dm_service._normalize_item_id("healing potion") == "potion_healing"
        assert dm_service._normalize_item_id("knife") == "dagger"
        assert dm_service._normalize_item_id("lockpicks") == "thieves_tools"

    def test_strips_whitespace(self, dm_service):
        """Leading/trailing whitespace is stripped."""
        assert dm_service._normalize_item_id("  sword  ") == "sword"


class TestCommerceAutoExecute:
    """Tests for auto-execute commerce fallback (PRP-18e).

    When the DM ignores commerce_sell/commerce_buy and uses blocked fields
    (gold_delta, inventory_remove, inventory_add), we auto-execute the
    transaction using the blocked data as intent signal.
    """

    def test_auto_sell_removes_item_adds_gold(self, dm_service, sample_character):
        """Auto-sell executes when DM uses inventory_remove during sell action."""
        # Add a sword to inventory (value=10, sell price=5)
        sample_character["inventory"] = [{
            "item_id": "sword",
            "name": "Sword",
            "quantity": 1,
            "item_type": "weapon",
            "description": "A sword",
        }]
        sample_character["gold"] = 0

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I want to sell my sword",
            blocked_items_remove=["sword"],
            blocked_items_add=None,
            blocked_gold=5,  # DM tried to add gold
        )

        assert len(result["sold"]) == 1
        assert result["sold"][0]["item"] == "sword"
        assert result["sold"][0]["gold"] == 5  # 50% of 10
        assert sample_character["gold"] == 5
        assert len(sample_character["inventory"]) == 0

    def test_auto_sell_decrements_quantity(self, dm_service, sample_character):
        """Auto-sell decrements quantity when item has qty > 1."""
        sample_character["inventory"] = [{
            "item_id": "torch",
            "name": "Torch",
            "quantity": 5,
            "item_type": "misc",
            "description": "A torch",
        }]
        sample_character["gold"] = 0

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="sell my torch",
            blocked_items_remove=["torch"],
            blocked_items_add=None,
            blocked_gold=1,
        )

        assert len(result["sold"]) == 1
        assert sample_character["inventory"][0]["quantity"] == 4
        assert sample_character["gold"] == 1  # torch value=1, 50%=0, min=1

    def test_auto_sell_skips_missing_items(self, dm_service, sample_character):
        """Items not in inventory are not auto-sold."""
        sample_character["inventory"] = []
        sample_character["gold"] = 0

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I sell my shield",
            blocked_items_remove=["shield"],
            blocked_items_add=None,
            blocked_gold=20,
        )

        assert len(result["sold"]) == 0
        assert sample_character["gold"] == 0  # Unchanged

    def test_auto_sell_only_on_sell_action(self, dm_service, sample_character):
        """Auto-sell doesn't trigger for non-sell actions."""
        sample_character["inventory"] = [{
            "item_id": "sword",
            "name": "Sword",
            "quantity": 1,
            "item_type": "weapon",
            "description": "A sword",
        }]
        sample_character["gold"] = 0

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I attack with my sword",  # Not a sell action
            blocked_items_remove=["sword"],
            blocked_items_add=None,
            blocked_gold=None,
        )

        assert len(result["sold"]) == 0
        assert len(sample_character["inventory"]) == 1  # Unchanged

    def test_auto_buy_deducts_gold_adds_item(self, dm_service, sample_character):
        """Auto-buy executes when DM uses inventory_add during buy action."""
        sample_character["inventory"] = []
        sample_character["gold"] = 50

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I want to buy a dagger",
            blocked_items_remove=None,
            blocked_items_add=["dagger"],
            blocked_gold=-3,  # DM tried to deduct gold
        )

        assert len(result["bought"]) == 1
        assert result["bought"][0]["item"] == "dagger"
        assert result["bought"][0]["gold"] == 3
        assert sample_character["gold"] == 47
        assert len(sample_character["inventory"]) == 1
        assert sample_character["inventory"][0]["item_id"] == "dagger"

    def test_auto_buy_requires_negative_gold(self, dm_service, sample_character):
        """Auto-buy only triggers when DM tried to deduct gold (negative)."""
        sample_character["inventory"] = []
        sample_character["gold"] = 50

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I want to buy a dagger",
            blocked_items_remove=None,
            blocked_items_add=["dagger"],
            blocked_gold=3,  # Positive gold (wrong direction)
        )

        assert len(result["bought"]) == 0
        assert sample_character["gold"] == 50  # Unchanged

    def test_auto_buy_insufficient_gold(self, dm_service, sample_character):
        """Auto-buy fails if player doesn't have enough gold."""
        sample_character["inventory"] = []
        sample_character["gold"] = 5

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I want to buy a sword",
            blocked_items_remove=None,
            blocked_items_add=["sword"],
            blocked_gold=-10,  # Sword costs 10, player has 5
        )

        assert len(result["bought"]) == 0
        assert sample_character["gold"] == 5  # Unchanged
        assert len(sample_character["inventory"]) == 0

    def test_auto_buy_skips_unknown_items(self, dm_service, sample_character):
        """Items not in catalog are not auto-bought."""
        sample_character["inventory"] = []
        sample_character["gold"] = 100

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I want to buy a vorpal blade",
            blocked_items_remove=None,
            blocked_items_add=["vorpal_blade"],
            blocked_gold=-50,
        )

        assert len(result["bought"]) == 0
        assert sample_character["gold"] == 100  # Unchanged

    def test_no_auto_execute_without_action(self, dm_service, sample_character):
        """Empty action string prevents auto-execute."""
        sample_character["inventory"] = [{
            "item_id": "sword",
            "name": "Sword",
            "quantity": 1,
            "item_type": "weapon",
            "description": "A sword",
        }]
        sample_character["gold"] = 50

        # This would be a sell, but no action provided
        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="",  # Empty action
            blocked_items_remove=["sword"],
            blocked_items_add=None,
            blocked_gold=5,
        )

        assert len(result["sold"]) == 0
        assert len(result["bought"]) == 0

    def test_auto_sell_uses_correct_price(self, dm_service, sample_character):
        """Auto-sell uses 50% of catalog value, ignoring DM's gold amount."""
        # chain_mail has value=40, so sell price should be 20
        sample_character["inventory"] = [{
            "item_id": "chain_mail",
            "name": "Chain Mail",
            "quantity": 1,
            "item_type": "armor",
            "description": "Chain mail armor",
        }]
        sample_character["gold"] = 0

        result = dm_service._auto_execute_commerce(
            character=sample_character,
            action="I sell my chain mail",
            blocked_items_remove=["chain_mail"],
            blocked_items_add=None,
            blocked_gold=10,  # DM gave wrong amount - should be ignored
        )

        # Should use catalog price (40 / 2 = 20), not DM's 10
        assert result["sold"][0]["gold"] == 20
        assert sample_character["gold"] == 20
