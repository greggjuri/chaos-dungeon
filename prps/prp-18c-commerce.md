# PRP-18c: Commerce System

**Created**: 2026-01-15
**Initial**: `initials/init-18c-commerce.md`
**Status**: Ready

---

## Overview

### Problem Statement
The item authority lockdown (init-18a) correctly blocks ALL DM gold/item grants to prevent exploitation. However, this also blocks legitimate commerce transactions. When players try to buy or sell items at shops, the server blocks the DM's `gold_delta` and `inventory_add` outputs, making commerce impossible.

### Proposed Solution
Add dedicated commerce fields to StateChanges that bypass the gold/item block:
- `commerce_sell`: Sell an item (server removes item, adds gold at 50% value)
- `commerce_buy`: Buy an item (server validates gold, deducts it, adds item)

The server validates and executes both sides of the transaction atomically, maintaining item authority while enabling the classic RPG buy/sell loop.

### Success Criteria
- [ ] Player can sell items at shops (item removed, gold gained at 50% value)
- [ ] Player can buy items at shops (gold deducted, item added)
- [ ] Insufficient gold rejects purchase with clear error
- [ ] Missing inventory item rejects sale with clear error
- [ ] Unknown item rejects purchase with clear error
- [ ] All transactions are atomic (both sides or neither)
- [ ] DM prompt includes commerce instructions
- [ ] Commerce detection triggers context injection

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Server authority architecture
- `docs/DECISIONS.md` - ADR-009 (Mistral), ADR-010 (cost protection)
- `initials/init-18a-item-authority.md` - Item authority lockdown this builds on
- `prps/prp-18a-item-authority.md` - Previous implementation blocking DM grants

### Dependencies
- **Required**: prp-18a-item-authority (complete) - Commerce builds on item authority
- **Required**: Existing item catalog (`lambdas/shared/items.py`)
- **Optional**: Future haggling system could use Charisma modifiers

### Files to Modify/Create
```
lambdas/dm/models.py              # Add commerce_sell, commerce_buy to StateChanges
lambdas/dm/service.py             # Add _process_commerce(), call in action flow
lambdas/dm/prompts/output_format.py  # Add commerce instructions
lambdas/dm/prompts/context.py     # Add build_commerce_context()
lambdas/shared/actions.py         # Add is_sell_action(), is_buy_action()
lambdas/tests/test_commerce.py    # NEW: Commerce unit tests
```

---

## Technical Specification

### Data Models

```python
# In lambdas/dm/models.py - Add to StateChanges

class StateChanges(BaseModel):
    # Existing fields
    hp_delta: int = 0
    gold_delta: int = 0  # Still blocked for direct grants
    xp_delta: int = 0
    inventory_add: list[str] = Field(default_factory=list)
    inventory_remove: list[str] = Field(default_factory=list)
    location: str | None = None
    world_state: dict[str, Any] = Field(default_factory=dict)
    item_used: str | None = None

    # NEW: Commerce fields (bypass gold/item block)
    commerce_sell: str | None = None
    """Item ID to sell. Server removes from inventory, adds 50% value as gold."""

    commerce_buy: CommerceTransaction | None = None
    """Purchase request. Server validates gold, deducts, adds item."""


class CommerceTransaction(BaseModel):
    """Buy transaction details from DM."""

    item: str
    """Item ID to purchase."""

    price: int
    """Gold cost (should match catalog price)."""
```

### API Changes
No new API endpoints. Commerce uses existing `/sessions/{id}/action` endpoint with new StateChanges fields parsed from DM response.

### Commerce Flow

**Selling:**
```
Player: "I want to sell my torch"
DM: Narrates sale, outputs commerce_sell: "torch"
Server:
  1. Validate torch in inventory
  2. Get value from ITEM_CATALOG (torch.value = 1)
  3. Calculate sell price (50% = 0, minimum 1 gold)
  4. Remove torch from inventory
  5. Add 1 gold to character
Result: Atomic transaction complete
```

**Buying:**
```
Player: "I want to buy a sword"
DM: Narrates purchase, outputs commerce_buy: {"item": "sword", "price": 10}
Server:
  1. Validate item exists in ITEM_CATALOG
  2. Validate player has >= 10 gold
  3. Deduct 10 gold from character
  4. Add sword to inventory
Result: Atomic transaction complete
```

---

## Implementation Steps

### Step 1: Add Commerce Models
**Files**: `lambdas/dm/models.py`

Add `CommerceTransaction` model and commerce fields to `StateChanges`.

```python
class CommerceTransaction(BaseModel):
    """Buy transaction details from DM."""

    item: str
    """Item ID to purchase."""

    price: int = Field(ge=0)
    """Gold cost (should match catalog price)."""


class StateChanges(BaseModel):
    # ... existing fields ...

    commerce_sell: str | None = None
    """Item ID to sell. Server removes from inventory, adds 50% value as gold."""

    commerce_buy: CommerceTransaction | None = None
    """Purchase request. Server validates gold, deducts, adds item."""
```

**Validation**:
- [ ] Model imports correctly
- [ ] Pydantic validates correctly

### Step 2: Add Commerce Detection
**Files**: `lambdas/shared/actions.py`

Add `is_sell_action()` and `is_buy_action()` functions alongside existing `is_search_action()`.

```python
# Patterns to detect sell attempts
SELL_PATTERNS = [
    r"\bsell\b",
    r"\btrade\b.*\bfor\b.*\bgold\b",
    r"\bexchange\b.*\bfor\b.*\b(gold|coin)\b",
    r"\bpawn\b",
]

# Patterns to detect buy attempts
BUY_PATTERNS = [
    r"\bbuy\b",
    r"\bpurchase\b",
    r"\bpay\b.*\bfor\b",
    r"\bacquire\b",
    r"\bget\b.*\bfrom\b.*\b(shop|merchant|vendor)\b",
]


def is_sell_action(action: str) -> bool:
    """Detect if player is trying to sell something."""
    action_lower = action.lower()
    for pattern in SELL_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("COMMERCE: Sell action detected", extra={"action": action[:100]})
            return True
    return False


def is_buy_action(action: str) -> bool:
    """Detect if player is trying to buy something."""
    action_lower = action.lower()
    for pattern in BUY_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("COMMERCE: Buy action detected", extra={"action": action[:100]})
            return True
    return False
```

**Validation**:
- [ ] Tests for sell detection patterns
- [ ] Tests for buy detection patterns

### Step 3: Add Commerce Context Builder
**Files**: `lambdas/dm/prompts/context.py`

Add `_format_commerce_context()` method to `DMPromptBuilder` class, called from `build_context()` when commerce action detected.

```python
def build_context(
    self,
    character: Character,
    session: Session,
    session_data: dict | None = None,
    action: str = "",
) -> str:
    """Build the dynamic context section.

    Args:
        character: Current player character
        session: Current game session
        session_data: Optional raw session dict for pending_loot access
        action: Player action text for commerce detection
    """
    parts = [
        self._format_character_block(character),
        self._format_world_state(session),
        self._format_message_history(session.message_history),
    ]

    # Add loot context if there's pending loot
    if session_data:
        loot_context = self._format_pending_loot(session_data)
        if loot_context:
            parts.append(loot_context)

    # Add commerce context if commerce action detected
    if action:
        commerce_context = self._format_commerce_context(character, action)
        if commerce_context:
            parts.append(commerce_context)

    return "\n\n".join(parts)


def _format_commerce_context(self, character: Character, action: str) -> str | None:
    """Format commerce context when buy/sell action detected.

    Args:
        character: Player character
        action: Player action text

    Returns:
        Commerce context block or None if not a commerce action
    """
    from shared.actions import is_buy_action, is_sell_action
    from shared.items import ITEM_CATALOG

    is_sell = is_sell_action(action)
    is_buy = is_buy_action(action)

    if not is_sell and not is_buy:
        return None

    gold = character.gold

    lines = ["## COMMERCE CONTEXT"]
    lines.append(f"Player has {gold} gold.")

    if is_sell and character.inventory:
        lines.append("")
        lines.append("SELLABLE ITEMS (50% value, minimum 1 gold):")
        for item in character.inventory:
            item_id = getattr(item, 'item_id', None) or item.name.lower().replace(" ", "_")
            item_def = ITEM_CATALOG.get(item_id)
            if item_def:
                sell_price = max(1, item_def.value // 2)
                lines.append(f"- {item_def.name} ({item_def.id}): {sell_price} gold")
            else:
                lines.append(f"- {item.name}: 1 gold (unknown item)")

    if is_buy:
        lines.append("")
        lines.append(f"Player can afford items up to {gold} gold.")
        lines.append("")
        lines.append("COMMON SHOP PRICES:")
        lines.append("- torch: 1 gold")
        lines.append("- dagger: 3 gold")
        lines.append("- rations: 5 gold")
        lines.append("- sword: 10 gold")
        lines.append("- shield: 10 gold")
        lines.append("- leather_armor: 10 gold")
        lines.append("- chain_mail: 40 gold")
        lines.append("- potion_healing: 50 gold")

    return "\n".join(lines)
```

**Validation**:
- [ ] Context includes sellable items with prices
- [ ] Context shows player gold and affordable items

### Step 4: Update DM Output Format
**Files**: `lambdas/dm/prompts/output_format.py`

Add commerce instructions section after the item authority section.

```python
# Add to OUTPUT_FORMAT string after ITEM AND GOLD AUTHORITY section:

## COMMERCE (BUYING AND SELLING)

When the player buys or sells items at a shop or merchant:

SELLING ITEMS:
- Use: commerce_sell: "<item_id>"
- Server removes item from inventory and adds gold (50% of item value, minimum 1)
- You narrate the transaction
- Example: commerce_sell: "torch"

BUYING ITEMS:
- Use: commerce_buy: {"item": "<item_id>", "price": <gold_amount>}
- Server validates gold, deducts it, and adds the item
- Use catalog prices from COMMERCE CONTEXT
- Example: commerce_buy: {"item": "sword", "price": 10}

IMPORTANT:
- Do NOT use gold_delta for commerce - it will be blocked
- Always use these commerce fields for buy/sell transactions
- If player can't afford something, narrate that they don't have enough gold
- If player doesn't have the item to sell, narrate that they don't have it
```

**Validation**:
- [ ] Instructions are clear and complete
- [ ] Examples match actual JSON format

### Step 5: Add Commerce Processing
**Files**: `lambdas/dm/service.py`

Add `_process_commerce()` method and call it from `_apply_state_changes()`.

```python
def _process_commerce(
    self,
    character: dict,
    state: StateChanges,
) -> dict:
    """Process buy/sell transactions server-side.

    Both sides of the transaction are atomic - if validation fails,
    nothing changes.

    Args:
        character: Character dict (will be modified in-place)
        state: StateChanges from DM response

    Returns:
        Result dict with sold/bought info or error
    """
    result = {"sold": None, "bought": None, "error": None}

    # Handle sell
    if state.commerce_sell:
        item_id = self._normalize_item_id(state.commerce_sell)
        inventory = character.get("inventory", [])

        # Find item in inventory
        item_index = self._find_inventory_item_index(inventory, item_id)

        if item_index is None:
            logger.warning(
                "COMMERCE: Sell failed - item not in inventory",
                extra={"item": item_id},
            )
            result["error"] = f"Cannot sell {item_id} - not in inventory"
        else:
            item_def = ITEM_CATALOG.get(item_id)
            # 50% value, minimum 1 gold
            sell_price = max(1, (item_def.value // 2) if item_def else 1)

            # Atomic: remove item AND add gold
            item = inventory[item_index]
            if isinstance(item, dict):
                qty = item.get("quantity", 1)
                if qty > 1:
                    inventory[item_index]["quantity"] = qty - 1
                else:
                    inventory.pop(item_index)
            else:
                inventory.pop(item_index)

            character["gold"] = character.get("gold", 0) + sell_price
            character["inventory"] = inventory

            result["sold"] = {"item": item_id, "gold": sell_price}
            logger.info("COMMERCE: Item sold", extra=result["sold"])

    # Handle buy
    if state.commerce_buy:
        buy_data = state.commerce_buy
        item_id = self._normalize_item_id(buy_data.item)
        price = buy_data.price

        current_gold = character.get("gold", 0)
        item_def = ITEM_CATALOG.get(item_id)

        if not item_def:
            logger.warning(
                "COMMERCE: Buy failed - unknown item",
                extra={"item": item_id},
            )
            result["error"] = f"Unknown item: {item_id}"
        elif price > current_gold:
            logger.warning(
                "COMMERCE: Buy failed - insufficient gold",
                extra={"price": price, "gold": current_gold},
            )
            result["error"] = f"Cannot afford {item_id} - costs {price}, have {current_gold}"
        else:
            # Atomic: deduct gold AND add item
            character["gold"] = current_gold - price
            self._add_item_to_inventory(character, item_def)

            result["bought"] = {"item": item_id, "gold": price}
            logger.info("COMMERCE: Item bought", extra=result["bought"])

    return result


def _normalize_item_id(self, item_name: str) -> str:
    """Normalize item name to catalog ID format.

    Args:
        item_name: Item name from DM output (may have spaces, mixed case)

    Returns:
        Normalized item ID (lowercase, underscores)
    """
    from shared.items import ITEM_ALIASES, ITEM_CATALOG

    normalized = item_name.lower().strip()

    # Try direct catalog lookup first
    if normalized in ITEM_CATALOG:
        return normalized

    # Try underscore conversion (e.g., "healing potion" -> "healing_potion")
    underscore_id = normalized.replace(" ", "_")
    if underscore_id in ITEM_CATALOG:
        return underscore_id

    # Check aliases
    if normalized in ITEM_ALIASES:
        return ITEM_ALIASES[normalized]

    return underscore_id


def _add_item_to_inventory(self, character: dict, item_def: ItemDefinition) -> None:
    """Add item to character inventory, handling quantity stacking.

    Args:
        character: Character dict (modified in-place)
        item_def: Item definition to add
    """
    inventory = character.get("inventory", [])

    # Check if item already in inventory
    for i, inv_item in enumerate(inventory):
        if isinstance(inv_item, dict) and inv_item.get("item_id") == item_def.id:
            # Increment quantity
            current_qty = inv_item.get("quantity", 1)
            inventory[i]["quantity"] = current_qty + 1
            logger.info(f"COMMERCE: Incremented {item_def.name} to {current_qty + 1}")
            character["inventory"] = inventory
            return

    # Add new item
    inventory.append({
        "item_id": item_def.id,
        "name": item_def.name,
        "quantity": 1,
        "item_type": item_def.item_type.value,
        "description": item_def.description,
    })
    logger.info(f"COMMERCE: Added new item {item_def.name}")
    character["inventory"] = inventory
```

Call from `_apply_state_changes()`:

```python
def _apply_state_changes(
    self,
    character: dict,
    session: dict,
    dm_response: DMResponse,
) -> tuple[dict, dict]:
    """Apply state changes from DM response."""
    state = dm_response.state_changes

    # ... existing gold_delta/inventory_add blocking ...

    # Process commerce BEFORE other changes (atomic transactions)
    commerce_result = self._process_commerce(character, state)
    if commerce_result.get("error"):
        logger.warning("Commerce error", extra={"error": commerce_result["error"]})

    # ... rest of existing logic ...
```

**Validation**:
- [ ] Sell removes item and adds gold
- [ ] Buy deducts gold and adds item
- [ ] Errors are logged and handled

### Step 6: Update Context Builder Call
**Files**: `lambdas/dm/service.py`

Update `_process_normal_action()` to pass action to context builder.

```python
# In _process_normal_action(), update the context call:
context = self.prompt_builder.build_context(char_model, sess_model, session, action)
```

**Validation**:
- [ ] Commerce context injected when commerce action detected

### Step 7: Write Unit Tests
**Files**: `lambdas/tests/test_commerce.py` (NEW)

```python
"""Tests for commerce system."""

import pytest
from dm.models import CommerceTransaction, StateChanges
from shared.actions import is_buy_action, is_sell_action


class TestCommerceDetection:
    """Tests for buy/sell action detection."""

    @pytest.mark.parametrize("action", [
        "I want to sell my torch",
        "sell the dagger",
        "I'd like to pawn this ring",
        "trade my sword for gold",
        "exchange this amulet for coins",
    ])
    def test_sell_patterns_detected(self, action):
        """Sell patterns are detected correctly."""
        assert is_sell_action(action) is True

    @pytest.mark.parametrize("action", [
        "I look around the shop",
        "I attack the merchant",
        "What do you have for sale?",
    ])
    def test_non_sell_not_detected(self, action):
        """Non-sell actions are not detected as sell."""
        assert is_sell_action(action) is False

    @pytest.mark.parametrize("action", [
        "I want to buy a sword",
        "purchase some rations",
        "I'll pay for a healing potion",
        "I'd like to acquire some armor",
    ])
    def test_buy_patterns_detected(self, action):
        """Buy patterns are detected correctly."""
        assert is_buy_action(action) is True

    @pytest.mark.parametrize("action", [
        "I look at the swords",
        "What's the price?",
        "I leave the shop",
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

    def test_commerce_transaction_price_validation(self):
        """Negative price is rejected."""
        with pytest.raises(ValueError):
            CommerceTransaction(item="sword", price=-5)

    def test_state_changes_with_commerce(self):
        """StateChanges accepts commerce fields."""
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

        assert result["sold"] == {"item": "torch", "gold": 1}  # min 1 gold
        assert sample_character["gold"] == 1
        assert len(sample_character["inventory"]) == 0

    def test_sell_minimum_price_is_one(self, dm_service, sample_character):
        """Items worth less than 2 gold sell for 1 gold minimum."""
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

        assert result["sold"]["gold"] == 1  # torch value=1, 50%=0, min=1

    def test_sell_missing_item_fails(self, dm_service, sample_character):
        """Cannot sell item not in inventory."""
        sample_character["inventory"] = []

        state = StateChanges(commerce_sell="torch")
        result = dm_service._process_commerce(sample_character, state)

        assert result["error"] is not None
        assert "not in inventory" in result["error"]

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

    def test_buy_unknown_item_fails(self, dm_service, sample_character):
        """Cannot buy item not in catalog."""
        sample_character["gold"] = 100

        state = StateChanges(
            commerce_buy=CommerceTransaction(item="magic_unobtainium", price=50)
        )
        result = dm_service._process_commerce(sample_character, state)

        assert result["error"] is not None
        assert "Unknown item" in result["error"]

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
```

**Validation**:
- [ ] All tests pass
- [ ] Coverage includes edge cases

---

## Testing Requirements

### Unit Tests
- Test sell detection patterns (10+ variations)
- Test buy detection patterns (10+ variations)
- Test sell removes item and adds gold
- Test sell minimum price is 1 gold
- Test sell missing item fails
- Test buy deducts gold and adds item
- Test buy insufficient gold fails
- Test buy unknown item fails
- Test buy stacks existing items
- Test sell decrements quantity

### Integration Tests
- End-to-end sell flow with DM
- End-to-end buy flow with DM
- Commerce context appears in DM prompt

### Manual Testing
1. Create character with starting equipment
2. Find a merchant/shop in game
3. "I want to sell my torch" - verify torch removed, gold gained
4. "I want to buy a sword" - verify gold deducted, sword added
5. Try to buy with insufficient gold - verify rejection

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites
- Backend deployed: `aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip`
- Frontend running: `cd frontend && npm run dev`
- Character with starting equipment and some gold

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Start new session, explore until finding a shop/merchant | Shop/merchant NPC responds | ☐ |
| 2 | Type "I want to sell my torch" | Torch removed from inventory, gold increases by 1 | ☐ |
| 3 | Check inventory panel | Torch no longer shown, gold updated | ☐ |
| 4 | Type "I want to buy a dagger" | Gold decreases by 3, dagger added to inventory | ☐ |
| 5 | Check inventory panel | Dagger shown, gold reduced | ☐ |
| 6 | Type "I want to buy chain mail" (costs 40) with insufficient gold | DM narrates "can't afford" | ☐ |
| 7 | Check inventory panel | Gold unchanged, no chain mail | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Sell item not owned | "sell my magic sword" (not in inventory) | DM narrates player doesn't have it | ☐ |
| Buy unknown item | "buy a flux capacitor" | DM narrates item not available | ☐ |
| Insufficient gold | "buy chain mail" with < 40 gold | DM narrates not enough gold | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] Inventory updates immediately after transaction
- [ ] Gold amount updates correctly
- [ ] No CORS errors

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Item not in inventory | Sell attempt for item player doesn't have | Log warning, return error in result |
| Insufficient gold | Buy attempt without enough gold | Log warning, return error in result |
| Unknown item | Buy attempt for non-catalog item | Log warning, return error in result |

### Edge Cases
- **Selling equipped item**: Allow for MVP (no equipment slots yet)
- **Shop doesn't have item**: All shops have all catalog items for MVP
- **DM outputs wrong price**: Trust DM price for MVP, log if significantly different
- **Selling last item in stack**: Remove from inventory entirely
- **Buying item already owned**: Increment quantity

---

## Cost Impact

### Claude API
- ~100 tokens added to prompts when commerce context is relevant
- Only included when sell/buy action detected
- Estimated: < $0.50/month additional

### AWS
- No new resources
- Minimal additional DynamoDB writes (within character update)
- Estimated: $0.00 additional

---

## Open Questions

1. **None** - spec is comprehensive and follows established patterns.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Spec is detailed with exact implementation |
| Feasibility | 10 | Follows existing patterns (loot claim, item authority) |
| Completeness | 9 | All cases covered, future enhancements noted |
| Alignment | 10 | Server authority, budget-friendly, simple MVP |
| **Overall** | 9.75 | Ready for implementation |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
