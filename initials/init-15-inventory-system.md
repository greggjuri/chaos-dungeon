# init-15-inventory-system

## Overview

Implement server-side inventory tracking to prevent item hallucination. Currently players can acquire items simply by describing having them, and the DM invents items freely (potions, keys, lockets) without any mechanical backing.

## Dependencies

- init-14-combat-polish (COMPLETE)

## Problem

The DM currently hallucinated:
- "carved key" - given by NPC
- "invisibility potion" - given by NPC  
- "silver locket, potion of healing" - found in room
- "leather pouch, ornate key, tattered scroll" - looted from corpse

None of these exist in any data structure. The player could claim "I drink my potion of healing" and the DM would comply, or claim "I use my +5 Vorpal Sword" and might get away with it.

## Proposed Solution

### 1. Starting Equipment by Class
Based on BECMI rules:
- **Fighter**: Sword, shield, chain mail, backpack, rations
- **Thief**: Dagger, leather armor, thieves' tools, backpack, rations
- **Cleric**: Mace, shield, chain mail, holy symbol, backpack, rations
- **Magic-User**: Dagger, staff, spellbook, robes, backpack, rations

### 2. Data Model
```python
class InventoryItem(BaseModel):
    id: str
    name: str
    item_type: str  # weapon, armor, consumable, quest, misc
    properties: dict  # damage_dice, ac_bonus, healing, etc.

class Character(BaseModel):
    # ... existing fields ...
    inventory: list[InventoryItem] = []
    equipped_weapon: str | None = None
    equipped_armor: str | None = None
```

### 3. Item Acquisition
Items can only be added through explicit server-side actions:
- **Loot**: Combat victory → roll on loot table → add to inventory
- **Buy**: Gold transaction → add item from shop list
- **Find**: DM includes `"give_items"` in response → server validates and adds
- **Quest reward**: Scripted additions

### 4. DM Prompt Constraints
Tell the DM:
- What items the player actually has
- Cannot give items not in the `give_items` response field
- Must reference actual inventory for player actions

### 5. UI Considerations
- Inventory panel/modal showing current items
- "Use item" action in combat (potions)
- Equipment display (weapon, armor)

## Out of Scope

- Item durability/degradation
- Crafting system
- Item enchantment
- Detailed weight/encumbrance
- Shops/merchants (can be separate init)

## Acceptance Criteria

- [ ] Characters start with class-appropriate equipment
- [ ] Inventory persists in session/character data
- [ ] DM cannot hallucinate items player doesn't have
- [ ] Item acquisition only through validated server actions
- [ ] Player can view their inventory
- [ ] Consumables (potions) can be used

## Cost Impact

Minimal - slightly larger session objects, no additional AI calls.

## Notes

This follows the same pattern as server-side dice rolling: take mechanical authority away from the AI to ensure game integrity.
