# PRP-15: Inventory System

**Created**: 2026-01-14
**Initial**: `initials/init-15-inventory-system.md`
**Status**: Ready

---

## Overview

### Problem Statement

The DM currently hallucinates items freely. Players acquire items by describing having them, and the DM invents items (potions, keys, lockets) without mechanical backing. A player could claim "I drink my potion of healing" or "I use my +5 Vorpal Sword" and the DM would comply.

This undermines game integrity - there's no meaningful resource management if items can appear at will.

### Proposed Solution

Implement server-side inventory tracking with:
1. **Starting equipment by class** - BECMI-accurate gear on character creation
2. **Item catalog** - Predefined items that can exist in the game
3. **Validated acquisition** - DM can only give items from the catalog
4. **Consumable usage** - USE_ITEM combat action for potions
5. **Inventory UI** - Frontend panel to view/use items

### Success Criteria

- [ ] Characters start with class-appropriate BECMI equipment
- [ ] Inventory persists in character data
- [ ] DM cannot give items not in the catalog
- [ ] Item acquisition validated on server side
- [ ] Potions usable via USE_ITEM combat action
- [ ] Player can view inventory in UI
- [ ] Item effects applied correctly (healing potions heal)

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Data models show `inventory: list[Item]`
- `docs/DECISIONS.md` - ADR-003 (BECMI rules)
- `lambdas/shared/models.py` - Existing Item model
- `lambdas/dm/models.py` - StateChanges with inventory_add/remove
- `lambdas/dm/service.py` - Already applies inventory changes (lines 1134-1150)

### Dependencies

- Required: None (existing inventory infrastructure is underutilized)
- Optional: Combat system (for USE_ITEM action) - already complete

### Files to Modify/Create

```
lambdas/shared/items.py           # NEW: Item catalog and starting equipment
lambdas/character/service.py      # Add starting equipment on create
lambdas/dm/service.py             # Validate item acquisition, implement USE_ITEM
lambdas/dm/models.py              # Add item_used field to StateChanges
lambdas/dm/prompts/context.py     # Enhance inventory display with properties
lambdas/dm/prompts/output_format.py # Update DM instructions for items
frontend/src/components/game/InventoryPanel.tsx  # NEW: Inventory UI
frontend/src/components/game/CharacterStatus.tsx # Show equipped items
```

---

## Technical Specification

### Data Models

```python
# lambdas/shared/items.py

from enum import Enum
from pydantic import BaseModel, Field

class ItemType(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST = "quest"
    MISC = "misc"

class ItemDefinition(BaseModel):
    """Item template from the catalog."""
    id: str  # Unique item ID (e.g., "potion_healing")
    name: str  # Display name
    item_type: ItemType
    description: str = ""
    # Combat properties
    damage_dice: str | None = None  # e.g., "1d8" for longsword
    ac_bonus: int = 0  # For armor/shields
    # Consumable properties
    healing: int = 0  # HP restored when used
    uses: int = 1  # Number of uses (consumables)
    # Economy
    value: int = 0  # Base value in gold

class InventoryItem(BaseModel):
    """Item instance in a character's inventory."""
    item_id: str  # References ItemDefinition.id
    name: str  # Display name (copied from definition)
    quantity: int = Field(default=1, ge=1)
    # Denormalized for display
    item_type: ItemType
    description: str = ""
```

### Item Catalog

```python
# lambdas/shared/items.py (continued)

ITEM_CATALOG: dict[str, ItemDefinition] = {
    # Weapons
    "sword": ItemDefinition(
        id="sword", name="Sword", item_type=ItemType.WEAPON,
        damage_dice="1d8", value=10,
        description="A trusty steel sword."
    ),
    "dagger": ItemDefinition(
        id="dagger", name="Dagger", item_type=ItemType.WEAPON,
        damage_dice="1d4", value=3,
        description="A sharp dagger, favored by thieves."
    ),
    "mace": ItemDefinition(
        id="mace", name="Mace", item_type=ItemType.WEAPON,
        damage_dice="1d6", value=5,
        description="A heavy mace blessed for holy work."
    ),
    "staff": ItemDefinition(
        id="staff", name="Staff", item_type=ItemType.WEAPON,
        damage_dice="1d4", value=1,
        description="A wooden staff, also useful as a focus."
    ),

    # Armor
    "chain_mail": ItemDefinition(
        id="chain_mail", name="Chain Mail", item_type=ItemType.ARMOR,
        ac_bonus=4, value=40,
        description="Interlocking metal rings providing solid protection."
    ),
    "leather_armor": ItemDefinition(
        id="leather_armor", name="Leather Armor", item_type=ItemType.ARMOR,
        ac_bonus=2, value=10,
        description="Lightweight leather protection."
    ),
    "shield": ItemDefinition(
        id="shield", name="Shield", item_type=ItemType.ARMOR,
        ac_bonus=1, value=10,
        description="A sturdy wooden shield."
    ),
    "robes": ItemDefinition(
        id="robes", name="Robes", item_type=ItemType.ARMOR,
        ac_bonus=0, value=5,
        description="Simple cloth robes favored by magic users."
    ),

    # Consumables
    "potion_healing": ItemDefinition(
        id="potion_healing", name="Potion of Healing", item_type=ItemType.CONSUMABLE,
        healing=8, uses=1, value=50,
        description="A red potion that restores 1d8 HP."
    ),
    "rations": ItemDefinition(
        id="rations", name="Rations", item_type=ItemType.CONSUMABLE,
        uses=7, value=5,
        description="A week's worth of trail rations."
    ),
    "torch": ItemDefinition(
        id="torch", name="Torch", item_type=ItemType.MISC,
        value=1,
        description="Provides light for about an hour."
    ),

    # Tools
    "thieves_tools": ItemDefinition(
        id="thieves_tools", name="Thieves' Tools", item_type=ItemType.MISC,
        value=25,
        description="Lockpicks and other tools of the trade."
    ),
    "holy_symbol": ItemDefinition(
        id="holy_symbol", name="Holy Symbol", item_type=ItemType.MISC,
        value=25,
        description="A sacred symbol of your deity."
    ),
    "spellbook": ItemDefinition(
        id="spellbook", name="Spellbook", item_type=ItemType.MISC,
        value=50,
        description="Contains your memorized spells."
    ),
    "backpack": ItemDefinition(
        id="backpack", name="Backpack", item_type=ItemType.MISC,
        value=5,
        description="Carries your adventuring gear."
    ),

    # Quest items (can be dynamically added by DM)
    "rusty_key": ItemDefinition(
        id="rusty_key", name="Rusty Key", item_type=ItemType.QUEST,
        value=0,
        description="An old, corroded key."
    ),
    "golden_key": ItemDefinition(
        id="golden_key", name="Golden Key", item_type=ItemType.QUEST,
        value=0,
        description="A gleaming golden key."
    ),
    "ancient_scroll": ItemDefinition(
        id="ancient_scroll", name="Ancient Scroll", item_type=ItemType.QUEST,
        value=0,
        description="A scroll covered in mysterious writing."
    ),
}

# Starting equipment by class (BECMI-accurate)
STARTING_EQUIPMENT: dict[str, list[str]] = {
    "fighter": ["sword", "shield", "chain_mail", "backpack", "rations", "torch"],
    "thief": ["dagger", "leather_armor", "thieves_tools", "backpack", "rations", "torch"],
    "cleric": ["mace", "shield", "chain_mail", "holy_symbol", "backpack", "rations"],
    "magic_user": ["dagger", "staff", "spellbook", "robes", "backpack", "rations"],
}
```

### API Changes

No new endpoints needed. Existing endpoints are enhanced:

| Method | Path | Change |
|--------|------|--------|
| POST | /characters | Now includes starting equipment |
| POST | /sessions/{id}/action | Validates inventory_add items |
| POST | /sessions/{id}/action | Supports USE_ITEM combat action |

### Response Changes

`CharacterSnapshot` now includes full item details:

```python
class CharacterSnapshot(BaseModel):
    # ... existing fields ...
    inventory: list[dict]  # Changed from list[str] to include item_id, item_type
```

---

## Implementation Steps

### Step 1: Create Item Catalog

**Files**: `lambdas/shared/items.py` (NEW)

Create the item catalog with BECMI-accurate items and starting equipment definitions.

```python
# See Technical Specification above for full content
```

**Validation**:
- [ ] File created with all item definitions
- [ ] STARTING_EQUIPMENT defined for all 4 classes
- [ ] Lint passes

### Step 2: Add Starting Equipment on Character Creation

**Files**: `lambdas/character/service.py`

Update `create_character` to populate inventory with class-appropriate gear.

```python
from shared.items import STARTING_EQUIPMENT, ITEM_CATALOG, InventoryItem

def create_character(self, user_id: str, request: CharacterCreateRequest) -> dict:
    # ... existing code ...

    # Get starting equipment for class
    equipment_ids = STARTING_EQUIPMENT.get(request.character_class, [])
    inventory = []
    for item_id in equipment_ids:
        if item_id in ITEM_CATALOG:
            item_def = ITEM_CATALOG[item_id]
            inventory.append({
                "item_id": item_id,
                "name": item_def.name,
                "quantity": 1,
                "item_type": item_def.item_type.value,
                "description": item_def.description,
            })

    character = {
        # ... existing fields ...
        "inventory": inventory,  # Was: []
    }
```

**Validation**:
- [ ] New fighter has sword, shield, chain mail
- [ ] New thief has dagger, leather armor, thieves' tools
- [ ] New cleric has mace, shield, chain mail, holy symbol
- [ ] New magic_user has dagger, staff, spellbook, robes
- [ ] Unit test passes

### Step 3: Validate Item Acquisition

**Files**: `lambdas/dm/service.py`

Update `_apply_state_changes` to validate items before adding to inventory.

```python
from shared.items import ITEM_CATALOG, normalize_item_name

def _apply_state_changes(self, character: dict, state: StateChanges) -> dict:
    # ... existing code ...

    inventory = character.get("inventory", [])
    inventory_ids = [item.get("item_id") for item in inventory if isinstance(item, dict)]

    for item_name in state.inventory_add:
        # Try to find item in catalog by name
        item_def = find_item_by_name(item_name)
        if item_def is None:
            logger.warning(f"DM tried to give unknown item: {item_name}")
            continue  # Skip unknown items silently

        if item_def.id not in inventory_ids:
            inventory.append({
                "item_id": item_def.id,
                "name": item_def.name,
                "quantity": 1,
                "item_type": item_def.item_type.value,
                "description": item_def.description,
            })
            inventory_ids.append(item_def.id)

    # ... rest of existing code ...
```

Add helper function to `shared/items.py`:

```python
# Expanded aliases for common variations
ITEM_ALIASES: dict[str, str] = {
    # Healing potions
    "healing potion": "potion_healing",
    "health potion": "potion_healing",
    "potion of health": "potion_healing",
    "red potion": "potion_healing",
    # Keys (default to rusty, specific names will match catalog directly)
    "key": "rusty_key",
    "old key": "rusty_key",
    "iron key": "rusty_key",
    # Scrolls
    "scroll": "ancient_scroll",
    "old scroll": "ancient_scroll",
    "parchment": "ancient_scroll",
}

# Keywords that indicate a narrative/quest item
QUEST_KEYWORDS = [
    "key", "letter", "note", "scroll", "ring", "amulet",
    "token", "locket", "pendant", "coin", "gem", "map",
    "journal", "book", "vial", "pouch", "badge", "seal",
]

def find_item_by_name(name: str) -> ItemDefinition | None:
    """Find item by name (case-insensitive, fuzzy match).

    If no catalog match found, creates dynamic quest items for
    narrative items like "ornate locket" or "bloody letter".
    """
    normalized = name.lower().strip()

    # Exact match first
    for item_def in ITEM_CATALOG.values():
        if item_def.name.lower() == normalized:
            return item_def

    # Partial match (item name contains search term)
    for item_def in ITEM_CATALOG.values():
        if normalized in item_def.name.lower():
            return item_def

    # Check aliases
    if normalized in ITEM_ALIASES:
        return ITEM_CATALOG.get(ITEM_ALIASES[normalized])

    # Dynamic quest item creation for narrative flexibility
    # If it sounds like a quest/misc item, create a generic entry
    if any(keyword in normalized for keyword in QUEST_KEYWORDS):
        return ItemDefinition(
            id=f"quest_{normalized.replace(' ', '_')[:30]}",
            name=name.title(),
            item_type=ItemType.QUEST,
            value=0,
            description=f"A mysterious {name.lower()}.",
        )

    return None
```

**NOTE**: The warning log `logger.warning(f"DM tried to give unknown item: {item_name}")`
should be visible in CloudWatch after deployment. Monitor this to inform future
catalog/alias expansions.

**Validation**:
- [ ] Known items (sword, potion) are added correctly
- [ ] Unknown mechanical items are logged and skipped
- [ ] Fuzzy matching works (e.g., "healing potion" → potion_healing)
- [ ] Narrative items with quest keywords get dynamic entries (e.g., "ornate locket")
- [ ] Unit tests pass

### Step 4: Implement USE_ITEM Combat Action

**Files**: `lambdas/dm/service.py`, `lambdas/dm/models.py`

Add item usage in combat for potions.

**IMPORTANT**: First verify/add the CombatActionType enum and CombatAction model:

```python
# In dm/models.py - ensure CombatActionType has USE_ITEM
class CombatActionType(str, Enum):
    ATTACK = "attack"
    DEFEND = "defend"
    FLEE = "flee"
    USE_ITEM = "use_item"  # Ensure this exists

# In dm/models.py - ensure CombatAction has item_id field
class CombatAction(BaseModel):
    action_type: CombatActionType
    target_id: str | None = None
    item_id: str | None = None  # For USE_ITEM action

# In dm/models.py - add to StateChanges
class StateChanges(BaseModel):
    # ... existing fields ...
    item_used: str | None = None
    """Item that was consumed this turn."""

# In dm/service.py - handle USE_ITEM action
def _handle_combat_action(self, ...):
    if combat_action.action_type == CombatActionType.USE_ITEM:
        return self._handle_use_item(
            session, character, combat_state, combat_enemies, session_id,
            combat_action.item_id
        )

def _handle_use_item(
    self,
    session: dict,
    character: dict,
    combat_state: CombatState,
    combat_enemies: list,
    session_id: str,
    item_id: str | None,
) -> dict:
    """Handle USE_ITEM combat action."""
    if not item_id:
        # Auto-select first healing potion
        inventory = character.get("inventory", [])
        for item in inventory:
            if isinstance(item, dict) and item.get("item_id") == "potion_healing":
                item_id = "potion_healing"
                break

    if not item_id:
        return self._build_combat_action_response(
            session, character, combat_state, combat_enemies,
            "You have no usable items!",
            [], None
        )

    # Find and consume item
    inventory = character.get("inventory", [])
    item_found = None
    new_inventory = []

    for item in inventory:
        if isinstance(item, dict) and item.get("item_id") == item_id and not item_found:
            item_found = item
            # Decrement quantity or remove
            if item.get("quantity", 1) > 1:
                new_inventory.append({**item, "quantity": item["quantity"] - 1})
            # else: don't add back (consumed)
        else:
            new_inventory.append(item)

    if not item_found:
        return self._build_combat_action_response(
            session, character, combat_state, combat_enemies,
            f"You don't have that item!",
            [], None
        )

    character["inventory"] = new_inventory

    # Apply item effect
    item_def = ITEM_CATALOG.get(item_id)
    narrative = ""
    state_changes = StateChanges()

    if item_def and item_def.healing > 0:
        # Healing potion - roll 1d8
        healing = roll_dice(1, 8)[0]
        old_hp = character["hp"]
        character["hp"] = min(character["max_hp"], old_hp + healing)
        actual_healing = character["hp"] - old_hp

        narrative = f"You drink the {item_def.name} and feel warmth spread through your body, restoring {actual_healing} HP."
        state_changes.hp_delta = actual_healing
        state_changes.item_used = item_def.name
        state_changes.inventory_remove = [item_def.name]
    else:
        narrative = f"You use the {item_found.get('name', 'item')}."

    # Enemies still attack after item use
    enemy_results = self.combat_resolver.resolve_enemy_phase(
        character, combat_enemies, False
    )

    # ... rest of combat round logic ...
```

**Validation**:
- [ ] USE_ITEM with potion_healing restores HP
- [ ] Potion is removed from inventory
- [ ] Enemies still attack after item use
- [ ] Error if no usable items
- [ ] Unit tests pass

---

### MANDATORY INTEGRATION TEST CHECKPOINT

**CRITICAL**: After completing Step 4, you MUST deploy and manually test before proceeding:

1. **Deploy to AWS**:
   ```bash
   cd lambdas
   zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
   aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip

   zip -r /tmp/char-update.zip character/ shared/ -x "*.pyc" -x "*__pycache__*"
   aws lambda update-function-code --function-name chaos-prod-character --zip-file fileb:///tmp/char-update.zip
   ```

2. **Build and deploy frontend**:
   ```bash
   cd frontend && npm run build
   aws s3 sync dist/ s3://chaos-prod-frontend/ --delete
   aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
   ```

3. **Manually test in browser** (chaos.jurigregg.com):
   - [ ] Create a Fighter → verify starting equipment in CharacterStatus
   - [ ] Acquire Potion of Healing (via DM or direct DB edit)
   - [ ] Enter combat
   - [ ] Use potion via USE_ITEM action
   - [ ] Verify HP increases and potion is removed from inventory

**Do NOT proceed to Step 5+ until this passes.** Unit tests will not catch frontend-backend integration issues.

---

### Step 5: Update DM Prompt with Inventory Context

**Files**: `lambdas/dm/prompts/context.py`, `lambdas/dm/prompts/output_format.py`

Enhance inventory display to show item types and hint at valid items.

```python
# In context.py
def _format_character_block(self, character: Character) -> str:
    # ... existing code ...

    # Format inventory with types
    if character.inventory:
        items = []
        for item in character.inventory:
            if isinstance(item, dict):
                item_type = item.get("item_type", "misc")
                items.append(f"{item.get('name', 'Unknown')} ({item_type})")
            else:
                items.append(str(item))
        inventory_str = ", ".join(items)
    else:
        inventory_str = "Empty"
```

```python
# In output_format.py - add positive guidance (no negative constraints)
# Add to the OUTPUT_FORMAT string, in the state_changes section:

ITEM_GUIDANCE = """
ITEMS YOU CAN GIVE:
- Weapons: Sword, Dagger, Mace, Staff
- Armor: Shield, Leather Armor, Chain Mail
- Consumables: Potion of Healing, Torch, Rations
- Quest items: Keys, scrolls, letters, tokens, jewelry (for story purposes)

When giving items, use these standard names so they appear in the player's inventory.
"""
```

**NOTE**: Use positive framing only. Avoid negative constraints like "do not give X".

**Validation**:
- [ ] Inventory shows item types in DM context
- [ ] DM receives guidance about valid items
- [ ] Manual test: DM gives reasonable items

### Step 6: Add Frontend Inventory Panel

**Files**: `frontend/src/components/game/InventoryPanel.tsx` (NEW)

Create a simple inventory display component.

```typescript
interface InventoryItem {
  item_id: string;
  name: string;
  quantity: number;
  item_type: string;
  description: string;
}

interface InventoryPanelProps {
  items: InventoryItem[];
  onUseItem?: (itemId: string) => void;
  inCombat?: boolean;
}

export function InventoryPanel({ items, onUseItem, inCombat }: InventoryPanelProps) {
  if (items.length === 0) {
    return (
      <div className="p-4 text-gray-500 italic">
        Your pack is empty.
      </div>
    );
  }

  const consumables = items.filter(i => i.item_type === 'consumable');
  const equipment = items.filter(i => ['weapon', 'armor'].includes(i.item_type));
  const other = items.filter(i => !['consumable', 'weapon', 'armor'].includes(i.item_type));

  return (
    <div className="space-y-4">
      {equipment.length > 0 && (
        <div>
          <h3 className="font-bold text-amber-400 mb-2">Equipment</h3>
          {equipment.map(item => (
            <div key={item.item_id} className="flex justify-between">
              <span>{item.name}</span>
              <span className="text-gray-500">x{item.quantity}</span>
            </div>
          ))}
        </div>
      )}

      {consumables.length > 0 && (
        <div>
          <h3 className="font-bold text-green-400 mb-2">Consumables</h3>
          {consumables.map(item => (
            <div key={item.item_id} className="flex justify-between items-center">
              <span>{item.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">x{item.quantity}</span>
                {inCombat && item.item_type === 'consumable' && onUseItem && (
                  <button
                    onClick={() => onUseItem(item.item_id)}
                    className="px-2 py-1 text-xs bg-green-600 hover:bg-green-500 rounded"
                  >
                    Use
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {other.length > 0 && (
        <div>
          <h3 className="font-bold text-gray-400 mb-2">Other</h3>
          {other.map(item => (
            <div key={item.item_id} className="flex justify-between">
              <span>{item.name}</span>
              <span className="text-gray-500">x{item.quantity}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Validation**:
- [ ] Component renders with items grouped by type
- [ ] "Use" button shows for consumables in combat
- [ ] Empty state displays message
- [ ] Lint passes

### Step 7: Integrate Inventory Panel

**Files**: `frontend/src/pages/GamePage.tsx` or equivalent

Add inventory panel to game UI, possibly as a collapsible section or modal.

```typescript
// Add state for inventory visibility
const [showInventory, setShowInventory] = useState(false);

// Add button to toggle
<button
  onClick={() => setShowInventory(!showInventory)}
  className="text-amber-400"
>
  Inventory ({character.inventory.length})
</button>

// Show panel when open
{showInventory && (
  <InventoryPanel
    items={character.inventory}
    inCombat={combatActive}
    onUseItem={handleUseItem}
  />
)}
```

**Validation**:
- [ ] Inventory button visible in UI
- [ ] Panel toggles on click
- [ ] Items display correctly
- [ ] Use item works in combat

---

## Testing Requirements

### Unit Tests

**`lambdas/tests/test_items.py`** (NEW):
- `test_starting_equipment_fighter` - Fighter gets sword, shield, chain mail
- `test_starting_equipment_thief` - Thief gets dagger, leather armor, tools
- `test_starting_equipment_cleric` - Cleric gets mace, shield, holy symbol
- `test_starting_equipment_magic_user` - Magic user gets staff, spellbook
- `test_find_item_exact_match` - "Sword" finds sword
- `test_find_item_fuzzy_match` - "healing potion" finds potion_healing
- `test_find_item_alias` - "red potion" finds potion_healing
- `test_find_item_dynamic_quest` - "ornate locket" creates dynamic quest item
- `test_find_item_unknown` - "Vorpal Blade" returns None (no quest keyword)

**`lambdas/tests/test_character_service.py`**:
- `test_create_fighter_has_starting_equipment` - Verify inventory populated

**`lambdas/tests/test_dm_service.py`**:
- `test_inventory_add_valid_item` - Known item added
- `test_inventory_add_unknown_item_skipped` - Unknown item not added
- `test_use_item_healing_potion` - HP restored, potion consumed
- `test_use_item_no_item` - Error message returned

### Integration Tests

- Full combat flow with potion usage
- Character creation with equipment verification

### Manual Testing

1. Create new character, verify starting equipment
2. Start adventure, acquire item from DM
3. Enter combat, use healing potion
4. Verify inventory updates correctly

---

## Integration Test Plan

### Prerequisites
- Backend deployed: Direct Lambda update
- Frontend built: `cd frontend && npm run build`
- Browser DevTools open

### Test Steps

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Create new Fighter | Inventory shows Sword, Shield, Chain Mail, Backpack, Rations, Torch | ☐ |
| 2 | Create new Thief | Inventory shows Dagger, Leather Armor, Thieves' Tools, etc. | ☐ |
| 3 | Play until DM gives item | Item appears in inventory with correct type | ☐ |
| 4 | Try to claim non-existent item | DM does not add it to inventory | ☐ |
| 5 | Enter combat with healing potion | "Use Item" action available | ☐ |
| 6 | Use healing potion | HP increases, potion removed from inventory | ☐ |
| 7 | Open inventory panel | Items grouped by type (equipment/consumables/other) | ☐ |

### Error Scenarios

| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Use item with none | USE_ITEM with empty consumables | "You have no usable items!" message | ☐ |
| DM gives invalid item | DM says "gives you a Vorpal Blade" | Item not added, logged as warning | ☐ |

### Browser Checks
- [ ] No errors in Console
- [ ] Inventory persists after page refresh
- [ ] Item use shows in narrative

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Unknown item | DM gives item not in catalog | Log warning, skip silently |
| No usable items | USE_ITEM with no consumables | Return message to player |
| Item not found | USE_ITEM with invalid item_id | Return message to player |

### Edge Cases

- **Player has multiple potions**: Decrement quantity instead of removing
- **Healing exceeds max HP**: Cap at max_hp
- **Legacy characters without item_id**: Handle gracefully (migrate on access)

---

## Cost Impact

### Claude API
- No additional AI calls
- Slightly more tokens in context (~50 for inventory)
- Estimated monthly impact: $0

### AWS
- No new resources
- Slightly larger DynamoDB items (~200 bytes per item)
- Estimated monthly impact: < $0.01

---

## Open Questions

1. **Should the DM be able to create new item types?** Current design: No, only catalog items. This ensures balance but limits creativity. Could add a "misc" item type for flavor items with no mechanics.

2. **How to handle shops/merchants?** Out of scope for this PRP. Could be a follow-up init for gold-based purchases.

3. **Should equipment affect AC/damage?** The models support it (`ac_bonus`, `damage_dice`) but combat resolver would need updates. Could be a follow-up.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Clear requirements, BECMI reference |
| Feasibility | 9 | Builds on existing inventory infrastructure |
| Completeness | 8 | Core features covered; equipment effects deferred |
| Alignment | 9 | Follows pattern of server-side authority (like combat) |
| **Overall** | 8.75 | High confidence - well-defined scope with existing patterns |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable

### Additions Applied (from user clarifications)

- [x] Quest item flexibility implemented (dynamic quest items via QUEST_KEYWORDS)
- [x] DM prompt uses positive constraints only
- [x] Aliases expanded for common variations (ITEM_ALIASES dict)
- [x] CombatActionType.USE_ITEM documented
- [x] CombatAction.item_id field documented
- [x] Mandatory integration test checkpoint added after Step 4
- [x] CloudWatch log monitoring noted for unknown items
