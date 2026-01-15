# init-18-loot-tables

## Overview

Implement a server-controlled loot system to replace free-form item giving. Instead of the DM inventing items on the fly, loot is pre-rolled from BECMI-style loot tables when combat ends or containers are searched.

## Problem

Currently, item acquisition relies on:
1. DM deciding to give items via `+item_name` in state changes
2. Server validating against catalog + QUEST_KEYWORDS
3. Dynamic item creation for unknown items

This allows players to potentially "wish" for items by suggesting them to the DM. While we've mitigated this with keyword filtering, a proper loot table system provides better game balance and authentic roguelike mechanics.

## Proposed Solution

### 1. Loot Tables (BECMI-style)

Define loot tables with weighted item rolls:

```python
LOOT_TABLES = {
    "goblin": {
        "gold": "1d6",
        "rolls": 1,
        "items": [
            {"weight": 50, "item": None},  # Nothing
            {"weight": 30, "item": "dagger"},
            {"weight": 15, "item": "rations"},
            {"weight": 5, "item": "potion_healing"},
        ]
    },
    "skeleton": {
        "gold": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 60, "item": None},
            {"weight": 25, "item": "rusty_key"},
            {"weight": 15, "item": "ancient_scroll"},
        ]
    },
    "chest_tier1": {
        "gold": "2d6",
        "rolls": 2,
        "items": [
            {"weight": 40, "item": "torch"},
            {"weight": 30, "item": "rations"},
            {"weight": 20, "item": "potion_healing"},
            {"weight": 10, "item": "dagger"},
        ]
    },
    "chest_tier2": {
        "gold": "3d6",
        "rolls": 2,
        "items": [
            {"weight": 35, "item": "potion_healing"},
            {"weight": 25, "item": "shield"},
            {"weight": 20, "item": "chain_mail"},
            {"weight": 15, "item": "sword"},
            {"weight": 5, "item": "golden_key"},
        ]
    },
    # Fallback for enemies not in bestiary
    "unknown_enemy": {
        "gold": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 70, "item": None},
            {"weight": 20, "item": "rations"},
            {"weight": 10, "item": "torch"},
        ]
    },
}
```

### 2. Loot Rolling on Combat Victory

When combat ends with player victory:

```python
def roll_combat_loot(defeated_enemies: list[dict]) -> dict:
    """Roll loot for all defeated enemies."""
    total_gold = 0
    items = []
    
    for enemy in defeated_enemies:
        table_name = enemy.get("loot_table", "unknown_enemy")
        table = LOOT_TABLES.get(table_name, LOOT_TABLES["unknown_enemy"])
        
        # Roll gold
        total_gold += roll_dice_string(table["gold"])
        
        # Roll items
        for _ in range(table["rolls"]):
            item = weighted_random_choice(table["items"])
            if item:
                items.append(item)
    
    return {"gold": total_gold, "items": items}
```

### 3. Pending Loot System

Store loot in session until player explicitly searches/loots:

```python
# In session state
session["pending_loot"] = {
    "gold": 15,
    "items": ["dagger", "potion_healing"],
    "source": "combat_victory"
}
```

DM prompt includes:
```
LOOT AVAILABLE: 15 gold, Dagger, Potion of Healing
Player must search/loot the bodies to claim these items.
When player searches, output the loot in state changes.
```

### 4. Loot Claiming Behavior

**Trigger**: Flexible with prompting
- The DM should naturally prompt the player after combat victory ("Do you search the bodies?")
- Server validates that `pending_loot` exists before allowing claim
- Reasonable synonyms count: "search", "loot", "take", "grab", "check bodies", etc.
- The AI interprets player intent; the server validates loot exists

**DM Prompt Guidance**:
```
After describing the combat victory, ask the player if they want to search the fallen enemies.
Accept reasonable variations: "search", "loot", "take their stuff", "check the bodies", etc.
```

### 5. Unclaimed Loot Behavior

**Rule**: Loot persists until next combat starts (middle ground)
- If player ignores loot and explores, it remains available
- If new combat begins, unclaimed loot is lost forever
- This creates meaningful choice without being punishingly harsh

```python
# On combat start, clear any pending loot
if session.get("pending_loot"):
    # Log for debugging, but silently discard
    logger.info(f"Unclaimed loot lost: {session['pending_loot']}")
    session["pending_loot"] = None
```

### 6. Sequential Combat Handling

**Rule**: New combat clears old pending loot
- Combat A ends → loot A available
- Player doesn't search → loot A still pending
- Combat B starts → loot A lost forever
- Combat B ends → loot B available

This prevents loot accumulation and creates urgency to search after victories.

### 7. Bestiary Updates

Add `loot_table` field to enemy definitions:

```python
BESTIARY = {
    "goblin": {
        "hp": 4,
        "ac": 13,
        "attack_bonus": 1,
        "damage": "1d6",
        "xp": 10,
        "loot_table": "goblin",  # ADD THIS
    },
    "skeleton": {
        "hp": 6,
        "ac": 13,
        "attack_bonus": 2,
        "damage": "1d6",
        "loot_table": "skeleton",
    },
    # ... other enemies
}
```

**Fallback**: Enemies without `loot_table` field use `"unknown_enemy"` table.

### 8. Item Catalog Validation

All items referenced in loot tables must exist in the item catalog. During implementation:
1. Cross-reference loot table items against existing catalog
2. Add any missing items to catalog (rusty_key, ancient_scroll, golden_key, etc.)
3. Ensure item IDs match catalog format (snake_case)

### 9. Container/Location Loot (Future)

For non-combat loot (chests, searches):

```python
# When DM describes a searchable location
session["searchable_containers"] = {
    "old_chest": {"loot_table": "chest_tier1", "searched": False},
    "dead_adventurer": {"loot_table": "adventurer_corpse", "searched": False},
}
```

## Implementation Phases

### Phase 1: Core Loot Tables (This Init)
- Create `lambdas/shared/loot.py` with loot tables and rolling functions
- Add `loot_table` to bestiary entries
- Add fallback `unknown_enemy` table
- Roll loot on combat victory
- Store as `pending_loot` in session
- Clear pending loot when new combat starts
- Update DM prompt to narrate available loot and prompt for search
- Player must "search" (flexible interpretation) to claim loot
- Validate all loot table items exist in catalog (add missing)

### Phase 2: Container Loot (Future Init)
- Named containers with pre-rolled loot
- DM can reference specific containers
- Search action claims container loot

### Phase 3: Shop System (Future Init)
- Merchants with fixed inventory
- Gold-based purchases
- Price negotiation?

## Data Model Changes

### Session State
```python
session["pending_loot"] = {
    "gold": int,
    "items": list[str],  # Item IDs
    "source": str,  # "combat_victory", "container", etc.
}
# Set to None when claimed or when new combat starts
```

### Enemy Definition
```python
{
    "name": "Goblin",
    "hp": 4,
    "ac": 13,
    "loot_table": "goblin",  # NEW - defaults to "unknown_enemy" if missing
}
```

## DM Prompt Changes

After combat victory:
```
COMBAT ENDED - VICTORY
Loot available from defeated enemies:
- Gold: 15
- Items: Dagger, Potion of Healing

Prompt the player to search the bodies. Accept reasonable variations like "search", 
"loot", "take", "grab their stuff", "check the bodies", etc.

When the player searches or loots the bodies, include in your response:
gold_delta: +15
inventory_add: ["Dagger", "Potion of Healing"]

Do NOT give loot until the player explicitly searches/loots.
If player declines or moves on, acknowledge their choice - loot remains available 
until they enter new combat.
```

## Out of Scope

- Shop/merchant system (init-19)
- Named NPC inventories
- Rare/legendary item drops
- Enchanted/magic items with special effects
- Item durability
- Partial looting (take some items, leave others)

## Acceptance Criteria

- [ ] Loot tables defined for common enemy types
- [ ] Fallback `unknown_enemy` table for unlisted enemies
- [ ] Combat victory triggers loot roll
- [ ] Loot stored in `pending_loot` session state
- [ ] DM informed of available loot with prompt guidance
- [ ] Player must search/loot to claim items (flexible interpretation)
- [ ] Gold and items added correctly on search
- [ ] Cannot loot same combat twice
- [ ] Pending loot cleared when new combat starts
- [ ] All loot table items exist in item catalog

## Cost Impact

Minimal - slightly more complex combat resolution, no additional AI calls.

## Notes

This follows the established pattern of server authority over game mechanics. The DM narrates and interprets player intent, but the server controls what's actually available and validates all claims against `pending_loot`.

Key principle: **Positive constraints** - The server tells the DM "here's what loot exists" rather than trying to prevent the DM from inventing loot.
