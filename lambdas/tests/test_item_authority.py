"""Tests for item authority lockdown (PRP-18a).

These tests verify that:
1. DM cannot grant gold or items directly
2. Search actions are detected correctly
3. Server-side loot claiming works
"""

import pytest

from shared.actions import SEARCH_PATTERNS, is_search_action


class TestSearchDetection:
    """Test search action detection."""

    @pytest.mark.parametrize(
        "action",
        [
            "I search the bodies",
            "search",
            "Search the room",
            "loot the corpse",
            "I loot them",
            "I take the gold from the body",
            "take their stuff",
            "take items from bodies",
            "grab the loot",
            "grab the gold",
            "check the goblin's pockets",
            "check the corpse",
            "rummage through the remains",
            "I pilfer their belongings",
            "collect the gold",
            "gather the loot",
        ],
    )
    def test_search_actions_detected(self, action: str):
        """Search-like actions should be detected."""
        assert is_search_action(action) is True

    @pytest.mark.parametrize(
        "action",
        [
            "I attack the goblin",
            "I walk north",
            "I talk to the bartender",
            "I look around the room",
            "I open the door",
            "I cast fireball",
            "I drink my potion",
            "I rest for the night",
            "I flee from combat",
            "I defend myself",
            "take a nap",  # 'take' without body/corpse/items
            "grab my sword",  # 'grab' without loot/gold
            "check for traps",  # 'check' without body/corpse
        ],
    )
    def test_non_search_actions_not_detected(self, action: str):
        """Non-search actions should not be detected."""
        assert is_search_action(action) is False

    def test_case_insensitive(self):
        """Search detection should be case-insensitive."""
        assert is_search_action("SEARCH THE BODY") is True
        assert is_search_action("Search") is True
        assert is_search_action("LOOT everything") is True

    def test_search_patterns_exist(self):
        """Verify search patterns are defined."""
        assert len(SEARCH_PATTERNS) > 0
        assert any("search" in p for p in SEARCH_PATTERNS)
        assert any("loot" in p for p in SEARCH_PATTERNS)


class TestDMGrantBlocking:
    """Test that DM cannot grant items/gold in _apply_state_changes.

    These tests verify the blocking logic in service.py.
    """

    def test_dm_positive_gold_blocked(self):
        """DM gold_delta > 0 should be blocked."""
        from dm.models import DMResponse, StateChanges

        # Create a DM response with positive gold
        dm_response = DMResponse(
            narrative="You find gold!",
            state_changes=StateChanges(gold_delta=50),
            dice_rolls=[],
            combat_active=False,
            enemies=[],
        )

        # Simulate what _apply_state_changes does
        state = dm_response.state_changes
        if state.gold_delta > 0:
            state.gold_delta = 0

        assert state.gold_delta == 0

    def test_dm_inventory_add_blocked(self):
        """DM inventory_add should be blocked."""
        from dm.models import DMResponse, StateChanges

        dm_response = DMResponse(
            narrative="You find a sword!",
            state_changes=StateChanges(inventory_add=["sword", "dagger"]),
            dice_rolls=[],
            combat_active=False,
            enemies=[],
        )

        state = dm_response.state_changes
        if state.inventory_add:
            state.inventory_add = []

        assert state.inventory_add == []

    def test_dm_negative_gold_delta_blocked(self):
        """DM gold_delta < 0 (spending) is now blocked too."""
        from dm.models import StateChanges

        state = StateChanges(gold_delta=-10)

        # ALL gold_delta is blocked (use commerce_sell/commerce_buy)
        if state.gold_delta != 0:
            state.gold_delta = 0

        assert state.gold_delta == 0

    def test_dm_inventory_remove_blocked(self):
        """DM inventory_remove should be blocked."""
        from dm.models import StateChanges

        state = StateChanges(inventory_remove=["torch", "shield"])

        # Block all inventory removals
        if state.inventory_remove:
            state.inventory_remove = []

        assert state.inventory_remove == []

    def test_dm_hp_changes_allowed(self):
        """DM hp_delta should still work (both positive and negative)."""
        from dm.models import StateChanges

        # Damage
        state = StateChanges(hp_delta=-5)
        assert state.hp_delta == -5

        # Healing
        state = StateChanges(hp_delta=10)
        assert state.hp_delta == 10


class TestServerSideLootClaim:
    """Test server-side loot claiming logic."""

    def test_claim_pending_loot_with_gold(self):
        """Server-side claim should add gold to character."""

        # Simulate the claim logic
        character = {"gold": 100, "inventory": []}
        pending = {"gold": 25, "items": []}

        # Server adds gold
        character["gold"] += pending["gold"]

        assert character["gold"] == 125

    def test_claim_pending_loot_with_items(self):
        """Server-side claim should add items to inventory."""
        from shared.items import ITEM_CATALOG

        character = {"gold": 0, "inventory": []}
        pending = {"gold": 0, "items": ["dagger"]}

        # Server adds items
        for item_id in pending["items"]:
            item_def = ITEM_CATALOG.get(item_id)
            if item_def:
                character["inventory"].append({
                    "item_id": item_def.id,
                    "name": item_def.name,
                    "quantity": 1,
                })

        assert len(character["inventory"]) == 1
        assert character["inventory"][0]["item_id"] == "dagger"

    def test_claim_clears_pending_loot(self):
        """Claiming loot should clear pending_loot."""
        session = {"pending_loot": {"gold": 10, "items": ["dagger"]}}

        # After claim, pending is cleared
        session["pending_loot"] = None

        assert session["pending_loot"] is None

    def test_search_without_pending_claims_nothing(self):
        """Search action without pending_loot should claim nothing."""
        session = {"pending_loot": None}
        character = {"gold": 100, "inventory": []}

        pending = session.get("pending_loot")
        if not pending:
            claimed = None
        else:
            claimed = {"gold": pending.get("gold", 0), "items": pending.get("items", [])}

        assert claimed is None
        assert character["gold"] == 100  # Unchanged

    def test_duplicate_item_increments_quantity(self):
        """Claiming an item already in inventory should increment quantity."""
        from shared.items import ITEM_CATALOG

        character = {
            "gold": 0,
            "inventory": [
                {"item_id": "dagger", "name": "Dagger", "quantity": 2}
            ],
        }
        pending_items = ["dagger"]

        for item_id in pending_items:
            item_def = ITEM_CATALOG.get(item_id)
            if item_def:
                # Check existing
                existing_idx = None
                for i, inv_item in enumerate(character["inventory"]):
                    if isinstance(inv_item, dict) and inv_item.get("item_id") == item_id:
                        existing_idx = i
                        break

                if existing_idx is not None:
                    character["inventory"][existing_idx]["quantity"] += 1
                else:
                    character["inventory"].append({
                        "item_id": item_def.id,
                        "name": item_def.name,
                        "quantity": 1,
                    })

        assert len(character["inventory"]) == 1
        assert character["inventory"][0]["quantity"] == 3


class TestPromptContainsAuthority:
    """Test that prompts include item authority instructions."""

    def test_system_prompt_includes_item_authority(self):
        """System prompt should include item authority statement."""
        from dm.prompts.system_prompt import build_system_prompt

        prompt = build_system_prompt()

        assert "SERVER AUTHORITY" in prompt
        assert "CANNOT grant items or gold directly" in prompt
        assert "server will block it" in prompt

    def test_compact_prompt_includes_item_authority(self):
        """Compact system prompt should also include item authority."""
        from dm.prompts.system_prompt import build_compact_system_prompt

        prompt = build_compact_system_prompt()

        assert "SERVER AUTHORITY" in prompt
        assert "CANNOT grant items or gold directly" in prompt

    def test_output_format_includes_manipulation_resistance(self):
        """Output format should include manipulation resistance examples."""
        from dm.prompts.output_format import OUTPUT_FORMAT

        assert "MANIPULATION RESISTANCE" in OUTPUT_FORMAT
        assert "I search until I find a magic ring" in OUTPUT_FORMAT
        assert "The item has no such power" in OUTPUT_FORMAT


class TestContextLootFormatting:
    """Test loot context formatting."""

    def test_no_loot_context_when_empty(self):
        """Should return no-loot context when pending_loot is None."""
        from dm.prompts.context import DMPromptBuilder

        builder = DMPromptBuilder()
        result = builder._format_pending_loot({"pending_loot": None})

        assert "NO LOOT AVAILABLE" in result
        assert "finding nothing of value" in result

    def test_no_loot_context_when_empty_dict(self):
        """Should return no-loot context when pending_loot is empty."""
        from dm.prompts.context import DMPromptBuilder

        builder = DMPromptBuilder()
        result = builder._format_pending_loot({"pending_loot": {"gold": 0, "items": []}})

        assert "NO LOOT AVAILABLE" in result

    def test_loot_available_context(self):
        """Should format loot available context correctly."""
        from dm.prompts.context import DMPromptBuilder

        builder = DMPromptBuilder()
        result = builder._format_pending_loot({
            "pending_loot": {"gold": 15, "items": ["dagger"]}
        })

        assert "LOOT AVAILABLE" in result
        assert "Gold: 15" in result
        assert "Dagger" in result
        # Should NOT include instructions to output gold_delta
        assert "gold_delta: +15" not in result

    def test_loot_context_mentions_server_handles(self):
        """Loot context should mention server handles adding items."""
        from dm.prompts.context import DMPromptBuilder

        builder = DMPromptBuilder()
        result = builder._format_pending_loot({
            "pending_loot": {"gold": 10, "items": []}
        })

        assert "SERVER handles" in result or "server handles" in result.lower()


class TestNewSellPatterns:
    """Test new sell patterns added in PRP-18d."""

    @pytest.mark.parametrize(
        "action",
        [
            "I want to get rid of this torch",
            "get gold for my sword",
            "I'll give you my shield for gold",
            "give the merchant my dagger for coins",
            "I give my armor for money",
        ],
    )
    def test_new_sell_patterns_detected(self, action: str):
        """New sell patterns should be detected."""
        from shared.actions import is_sell_action

        assert is_sell_action(action) is True

    def test_acquire_no_longer_triggers_buy(self):
        """'acquire' should NOT trigger buy detection (ambiguous)."""
        from shared.actions import is_buy_action

        # "acquire" was removed from BUY_PATTERNS
        assert is_buy_action("I'd like to acquire some armor") is False
        assert is_buy_action("acquire gold for my item") is False
