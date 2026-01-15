# init-18c-commerce

## Overview

Add a server-controlled commerce system for buying and selling items. Currently, players cannot legitimately gain gold from selling items or spend gold to buy items - the DM's attempts to process transactions get blocked by init-18a's item authority lockdown.

## Problem

Testing revealed:
- Player sold torch to shopkeeper
- DM narrated receiving 5 gold
- Server blocked `gold_delta: +5` (correct per 18a rules)
- Player got nothing for the sale

The item authority lockdown (init-18a) correctly blocks ALL DM gold/item grants. But we have no legitimate channel for commerce transactions.

## Solution

Add dedicated commerce fields to StateChanges that bypass the gold/item block:
- `commerce_sell`: Sell an item (remove item, add gold)
- `commerce_buy`: Buy an item (remove gold, add item)

The server validates and executes both sides of the transaction atomically.

## Design Principles

1. **Server authority**: Server validates all transactions
2. **Atomic transactions**: Both sides (item AND gold) process together or not at all
3. **Simple pricing**: 50% sell value (standard RPG convention), buy at full catalog price
4. **No inventory limits on shops**: Buy any catalog item (for MVP simplicity)

## Commerce Flow

### Selling
```
Player: "I want to sell my torch"
DM detects sell intent, checks player inventory
DM outputs: commerce_sell: "torch"
Server: validates item in inventory, calculates 50% value, removes item, adds gold
Result: torch removed, gold added
```

### Buying
```
Player: "I want to buy a sword"
DM detects buy intent, checks player gold
DM outputs: commerce_buy: {"item": "sword", "price": 10}
Server: validates gold sufficient, validates item exists, deducts gold, adds item
Result: gold deducted, sword added
```

## Implementation

### 1. StateChanges Model Update

Add commerce fields:

```python
class StateChanges(BaseModel):
    # Existing fields
    hp_delta: int = 0
    gold_delta: int = 0  # Still blocked for direct grants
    xp_delta: int = 0
    inventory_add: list[str] = []
    inventory_remove: list[str] = []
    location: str | None = None
    
    # NEW: Commerce fields (bypass gold/item block)
    commerce_sell: str | None = None  # Item ID to sell
    commerce_buy: dict | None = None  # {"item": str, "price": int}
```

### 2. Commerce Processing in Service

```python
def _process_commerce(self, character: dict, state: StateChanges) -> dict:
    """Process buy/sell transactions server-side."""
    result = {"sold": None, "bought": None, "error": None}
    
    # Handle sell
    if state.commerce_sell:
        item_id = self._normalize_item_id(state.commerce_sell)
        inventory = character.get("inventory", [])
        
        # Find item in inventory
        item_index = next(
            (i for i, item in enumerate(inventory) if item.get("id") == item_id),
            None
        )
        
        if item_index is None:
            logger.warning("COMMERCE: Sell failed - item not in inventory", 
                extra={"item": item_id})
            result["error"] = f"Cannot sell {item_id} - not in inventory"
        else:
            item_def = ITEM_CATALOG.get(item_id)
            sell_price = (item_def.value // 2) if item_def else 1
            
            # Atomic: remove item AND add gold
            inventory.pop(item_index)
            character["gold"] = character.get("gold", 0) + sell_price
            
            result["sold"] = {"item": item_id, "gold": sell_price}
            logger.info("COMMERCE: Item sold", extra=result["sold"])
    
    # Handle buy
    if state.commerce_buy:
        buy_data = state.commerce_buy
        item_id = self._normalize_item_id(buy_data.get("item", ""))
        price = buy_data.get("price", 0)
        
        current_gold = character.get("gold", 0)
        item_def = ITEM_CATALOG.get(item_id)
        
        if not item_def:
            logger.warning("COMMERCE: Buy failed - unknown item", extra={"item": item_id})
            result["error"] = f"Unknown item: {item_id}"
        elif price > current_gold:
            logger.warning("COMMERCE: Buy failed - insufficient gold",
                extra={"price": price, "gold": current_gold})
            result["error"] = f"Cannot afford {item_id} - costs {price}, have {current_gold}"
        else:
            # Atomic: deduct gold AND add item
            character["gold"] = current_gold - price
            self._add_item_to_inventory(character, item_def)
            
            result["bought"] = {"item": item_id, "gold": price}
            logger.info("COMMERCE: Item bought", extra=result["bought"])
    
    return result
```

### 3. DM Prompt Updates

#### Output Format Addition

```
## COMMERCE

When the player buys or sells items at a shop or merchant:

SELLING ITEMS:
- Use: commerce_sell: "<item_id>"
- Server removes item from inventory and adds gold (50% of item value)
- You narrate the transaction
- Example: commerce_sell: "torch"

BUYING ITEMS:
- Use: commerce_buy: {"item": "<item_id>", "price": <gold_amount>}
- Server validates gold, deducts it, and adds the item
- Use catalog prices (sword=10, shield=10, chain_mail=40, etc.)
- Example: commerce_buy: {"item": "sword", "price": 10}

IMPORTANT:
- Do NOT use gold_delta for commerce - it will be blocked
- Always use these commerce fields for buy/sell transactions
- If player can't afford something, narrate that they don't have enough gold
```

#### Commerce Context (when player attempts commerce)

```python
def build_commerce_context(character: dict, action: str) -> str:
    """Build context for commerce actions."""
    
    # Detect commerce intent
    is_sell = is_sell_action(action)
    is_buy = is_buy_action(action)
    
    if not is_sell and not is_buy:
        return ""
    
    gold = character.get("gold", 0)
    inventory = character.get("inventory", [])
    
    lines = ["## COMMERCE CONTEXT"]
    lines.append(f"Player has {gold} gold.")
    
    if is_sell and inventory:
        lines.append("\nSellable items (50% value):")
        for item in inventory:
            item_def = ITEM_CATALOG.get(item.get("id"))
            if item_def:
                sell_price = item_def.value // 2
                lines.append(f"- {item_def.name} ({item_def.id}): {sell_price} gold")
    
    if is_buy:
        lines.append(f"\nPlayer can afford items up to {gold} gold.")
        lines.append("Common prices: torch=1, rations=5, dagger=3, sword=10, shield=10")
    
    return "\n".join(lines)
```

### 4. Commerce Detection

```python
# In shared/actions.py

SELL_PATTERNS = [
    r"\bsell\b",
    r"\btrade\b.*\bfor\b.*\bgold\b",
    r"\bexchange\b.*\bfor\b.*\b(gold|coin)\b",
    r"\bpawn\b",
]

BUY_PATTERNS = [
    r"\bbuy\b",
    r"\bpurchase\b",
    r"\bpay\b.*\bfor\b",
    r"\bacquire\b",
]

def is_sell_action(action: str) -> bool:
    """Detect if player is trying to sell something."""
    action_lower = action.lower()
    return any(re.search(pattern, action_lower) for pattern in SELL_PATTERNS)

def is_buy_action(action: str) -> bool:
    """Detect if player is trying to buy something."""
    action_lower = action.lower()
    return any(re.search(pattern, action_lower) for pattern in BUY_PATTERNS)
```

## Item Pricing Reference

For DM context, include standard prices:

| Item | Buy Price | Sell Price (50%) |
|------|-----------|------------------|
| Torch | 1 | 0 (minimum 1) |
| Rations | 5 | 2 |
| Dagger | 3 | 1 |
| Sword | 10 | 5 |
| Shield | 10 | 5 |
| Chain Mail | 40 | 20 |
| Potion of Healing | 50 | 25 |

Sell price minimum is 1 gold (can't sell for 0).

## Files to Modify

```
lambdas/dm/models.py            # Add commerce_sell, commerce_buy to StateChanges
lambdas/dm/service.py           # Add _process_commerce(), call it in action flow
lambdas/dm/prompts/context.py   # Add build_commerce_context()
lambdas/dm/prompts/output_format.py  # Add commerce instructions
lambdas/shared/actions.py       # Add is_sell_action(), is_buy_action()
lambdas/tests/test_commerce.py  # NEW: Commerce unit tests
```

## Acceptance Criteria

- [ ] `commerce_sell` field added to StateChanges
- [ ] `commerce_buy` field added to StateChanges
- [ ] Selling removes item and adds gold (50% value)
- [ ] Buying deducts gold and adds item
- [ ] Insufficient gold rejects purchase with error
- [ ] Missing item rejects sale with error
- [ ] Unknown item rejects purchase with error
- [ ] DM prompt includes commerce instructions
- [ ] Commerce context shows sellable items with prices
- [ ] `is_sell_action()` detects sell attempts
- [ ] `is_buy_action()` detects buy attempts

## Testing

### Manual Test: Selling
1. Have items in inventory (e.g., torch, dagger)
2. Find a merchant/shopkeeper
3. "I want to sell my torch"
4. Verify torch removed from inventory
5. Verify gold increased (by 50% of torch value, minimum 1)

### Manual Test: Buying
1. Have sufficient gold
2. At a shop, "I want to buy a sword"
3. Verify gold decreased by sword price (10)
4. Verify sword added to inventory

### Manual Test: Insufficient Gold
1. Have less than 10 gold
2. Try to buy sword (costs 10)
3. Verify purchase rejected
4. Verify gold unchanged, no item added

### Unit Tests
```python
def test_sell_removes_item_adds_gold():
    """Selling item removes it and adds 50% value."""

def test_sell_minimum_price_is_one():
    """Items worth 1 gold sell for 1, not 0."""

def test_sell_missing_item_fails():
    """Can't sell item not in inventory."""

def test_buy_deducts_gold_adds_item():
    """Buying item deducts gold and adds item."""

def test_buy_insufficient_gold_fails():
    """Can't buy if not enough gold."""

def test_buy_unknown_item_fails():
    """Can't buy item not in catalog."""

def test_is_sell_action_patterns():
    """Sell patterns detected correctly."""

def test_is_buy_action_patterns():
    """Buy patterns detected correctly."""
```

## Edge Cases

### What if player sells equipped item?
For MVP: Allow it. Item is removed regardless of equipped status. Future init could add "unequip first" requirement.

### What if shop doesn't have the item?
For MVP: All shops have all catalog items. Future init could add shop-specific inventories.

### What about haggling/negotiation?
Out of scope. Fixed prices for MVP. Future init could add Charisma-based price modifiers.

### What if DM outputs wrong price?
Server could validate against catalog price, but for MVP trust the DM's price output. Log if significantly different from catalog.

## Cost Impact

Minimal:
- ~100 tokens added to prompts when commerce context is relevant
- Only included when sell/buy action detected
- Estimated: < $0.50/month additional

## Future Enhancements (Out of Scope)

- Shop-specific inventories
- Price variation by location
- Charisma-based haggling
- Bulk buy/sell
- Item condition affecting price
- Stolen goods mechanics

## Notes

This follows the established pattern:
- Server authority over transactions
- DM provides narrative context
- Dedicated fields bypass the general block
- Atomic transactions (both sides succeed or fail together)

The commerce system is intentionally simple. Kill things, get loot, sell loot, buy better gear, kill harder things. Classic roguelike loop.
