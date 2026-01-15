# PRP-18: Loot Tables

**Created**: 2026-01-15
**Initial**: `initials/init-18-loot-tables.md`
**Status**: Ready

---

## Overview

### Problem Statement

Currently, item acquisition relies on the DM deciding to give items via `+item_name` in state changes. While server validation prevents completely invalid items, players can still "wish" for items by suggesting them to the DM. This undermines game balance and authentic roguelike mechanics.

The DM can give any item that matches the catalog or QUEST_KEYWORDS, which is too permissive. We need server-controlled loot generation that follows BECMI-style loot tables.

### Proposed Solution

Implement a loot table system that:
1. Pre-rolls loot when combat ends (based on defeated enemy types)
2. Stores loot as `pending_loot` in session state
3. Informs DM of available loot via prompt
4. Requires player to explicitly "search" to claim loot
5. Clears unclaimed loot when new combat starts

This follows the established pattern of **server authority** over game mechanics and **positive constraints** (telling DM what exists rather than blocking).

### Success Criteria
- [ ] Loot tables defined for all bestiary enemies
- [ ] Combat victory rolls loot from appropriate tables
- [ ] `pending_loot` stored in session state
- [ ] DM prompt includes available loot info
- [ ] Player must search/loot to claim items
- [ ] Gold and items added correctly on search
- [ ] Unclaimed loot cleared on new combat
- [ ] All loot table items exist in item catalog

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Server authority pattern
- `docs/DECISIONS.md` - ADR-010 (positive constraints approach)
- `initials/init-18-loot-tables.md` - Full specification

### Dependencies
- Required: prp-15-inventory-system.md (Complete) - Item catalog and validation
- Required: prp-12-turn-based-combat.md (Complete) - Combat resolution

### Files to Modify/Create
```
lambdas/shared/loot.py              # NEW: Loot tables and rolling functions
lambdas/dm/bestiary.py              # Add loot_table field to enemies
lambdas/dm/service.py               # Roll loot on victory, check pending on search
lambdas/dm/prompts/context.py       # Include pending_loot in DM prompt
lambdas/shared/items.py             # Add any missing items from loot tables
lambdas/tests/test_loot.py          # NEW: Unit tests for loot module
```

---

## Technical Specification

### Data Models

```python
# In lambdas/shared/loot.py

from pydantic import BaseModel

class LootTableEntry(BaseModel):
    """Single weighted entry in a loot table."""
    weight: int
    item: str | None  # None = no drop

class LootTable(BaseModel):
    """Complete loot table for an enemy or container."""
    gold_dice: str  # e.g., "1d6", "2d4"
    rolls: int      # Number of item rolls
    items: list[LootTableEntry]

class PendingLoot(BaseModel):
    """Loot waiting to be claimed by player."""
    gold: int
    items: list[str]  # Item IDs
    source: str       # "combat_victory", "container", etc.
```

### Session State Changes

```python
# New field in session dict
session["pending_loot"] = {
    "gold": 15,
    "items": ["dagger", "potion_healing"],
    "source": "combat_victory"
}
# Set to None when claimed or when new combat starts
```

### Bestiary Changes

```python
# Add loot_table field to BESTIARY entries
"goblin": {
    "name": "Goblin",
    "hp_dice": "1d6",
    "ac": 12,
    "attack_bonus": 1,
    "damage_dice": "1d6",
    "xp_value": 10,
    "loot_table": "goblin",  # NEW
},
```

### API Changes

No API changes required. The action endpoint already returns `state_changes` with gold and items.

---

## Implementation Steps

### Step 1: Create Loot Module
**Files**: `lambdas/shared/loot.py`

Create loot tables and rolling functions.

```python
"""Loot tables and rolling functions for Chaos Dungeon.

Implements BECMI-style loot generation from weighted tables.
Loot is rolled server-side when combat ends.
"""

import random
from aws_lambda_powertools import Logger
from shared.dice import roll as roll_dice

logger = Logger(child=True)

# =============================================================================
# LOOT TABLES - Weighted item drops by enemy/container type
# =============================================================================

LOOT_TABLES: dict[str, dict] = {
    # Basic enemies
    "goblin": {
        "gold_dice": "1d6",
        "rolls": 1,
        "items": [
            {"weight": 50, "item": None},
            {"weight": 30, "item": "dagger"},
            {"weight": 15, "item": "rations"},
            {"weight": 5, "item": "potion_healing"},
        ]
    },
    "kobold": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 60, "item": None},
            {"weight": 25, "item": "torch"},
            {"weight": 15, "item": "dagger"},
        ]
    },
    "skeleton": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 55, "item": None},
            {"weight": 25, "item": "rusty_key"},
            {"weight": 15, "item": "ancient_scroll"},
            {"weight": 5, "item": "sword"},
        ]
    },
    "giant_rat": {
        "gold_dice": "1d3",
        "rolls": 1,
        "items": [
            {"weight": 80, "item": None},
            {"weight": 20, "item": "rations"},
        ]
    },
    # Medium enemies
    "orc": {
        "gold_dice": "2d6",
        "rolls": 1,
        "items": [
            {"weight": 40, "item": None},
            {"weight": 30, "item": "sword"},
            {"weight": 20, "item": "shield"},
            {"weight": 10, "item": "potion_healing"},
        ]
    },
    "zombie": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 70, "item": None},
            {"weight": 20, "item": "rusty_key"},
            {"weight": 10, "item": "ancient_scroll"},
        ]
    },
    "hobgoblin": {
        "gold_dice": "2d6",
        "rolls": 1,
        "items": [
            {"weight": 35, "item": None},
            {"weight": 30, "item": "sword"},
            {"weight": 20, "item": "chain_mail"},
            {"weight": 15, "item": "potion_healing"},
        ]
    },
    "wolf": {
        "gold_dice": "0d0",  # No gold from animals
        "rolls": 1,
        "items": [
            {"weight": 70, "item": None},
            {"weight": 30, "item": "rations"},  # Meat
        ]
    },
    # Tougher enemies
    "giant_spider": {
        "gold_dice": "1d6",
        "rolls": 1,
        "items": [
            {"weight": 60, "item": None},
            {"weight": 25, "item": "ancient_scroll"},
            {"weight": 15, "item": "potion_healing"},
        ]
    },
    "ghoul": {
        "gold_dice": "2d6",
        "rolls": 1,
        "items": [
            {"weight": 50, "item": None},
            {"weight": 25, "item": "rusty_key"},
            {"weight": 15, "item": "golden_key"},
            {"weight": 10, "item": "potion_healing"},
        ]
    },
    "bugbear": {
        "gold_dice": "3d6",
        "rolls": 2,
        "items": [
            {"weight": 30, "item": None},
            {"weight": 25, "item": "sword"},
            {"weight": 20, "item": "shield"},
            {"weight": 15, "item": "potion_healing"},
            {"weight": 10, "item": "chain_mail"},
        ]
    },
    "ogre": {
        "gold_dice": "4d6",
        "rolls": 2,
        "items": [
            {"weight": 25, "item": None},
            {"weight": 25, "item": "potion_healing"},
            {"weight": 20, "item": "sword"},
            {"weight": 15, "item": "chain_mail"},
            {"weight": 15, "item": "golden_key"},
        ]
    },
    # Dangerous enemies
    "troll": {
        "gold_dice": "5d6",
        "rolls": 2,
        "items": [
            {"weight": 20, "item": None},
            {"weight": 30, "item": "potion_healing"},
            {"weight": 25, "item": "sword"},
            {"weight": 15, "item": "chain_mail"},
            {"weight": 10, "item": "golden_key"},
        ]
    },
    "wight": {
        "gold_dice": "3d6",
        "rolls": 2,
        "items": [
            {"weight": 30, "item": None},
            {"weight": 25, "item": "ancient_scroll"},
            {"weight": 20, "item": "golden_key"},
            {"weight": 15, "item": "potion_healing"},
            {"weight": 10, "item": "sword"},
        ]
    },
    "wraith": {
        "gold_dice": "4d6",
        "rolls": 2,
        "items": [
            {"weight": 35, "item": None},
            {"weight": 30, "item": "ancient_scroll"},
            {"weight": 20, "item": "golden_key"},
            {"weight": 15, "item": "potion_healing"},
        ]
    },
    # Boss enemies
    "vampire": {
        "gold_dice": "10d6",
        "rolls": 3,
        "items": [
            {"weight": 10, "item": None},
            {"weight": 30, "item": "potion_healing"},
            {"weight": 25, "item": "golden_key"},
            {"weight": 20, "item": "ancient_scroll"},
            {"weight": 15, "item": "chain_mail"},
        ]
    },
    "dragon": {
        "gold_dice": "20d6",
        "rolls": 4,
        "items": [
            {"weight": 5, "item": None},
            {"weight": 30, "item": "potion_healing"},
            {"weight": 25, "item": "golden_key"},
            {"weight": 20, "item": "sword"},
            {"weight": 20, "item": "chain_mail"},
        ]
    },
    # Fallback for unknown enemies
    "unknown_enemy": {
        "gold_dice": "1d4",
        "rolls": 1,
        "items": [
            {"weight": 70, "item": None},
            {"weight": 20, "item": "rations"},
            {"weight": 10, "item": "torch"},
        ]
    },
}


def weighted_random_choice(items: list[dict]) -> str | None:
    """Select item from weighted list.

    Args:
        items: List of {"weight": int, "item": str|None}

    Returns:
        Selected item ID or None
    """
    total_weight = sum(entry["weight"] for entry in items)
    roll = random.randint(1, total_weight)

    cumulative = 0
    for entry in items:
        cumulative += entry["weight"]
        if roll <= cumulative:
            return entry["item"]

    return None  # Shouldn't happen


def roll_enemy_loot(enemy_type: str) -> dict:
    """Roll loot for a single defeated enemy.

    Args:
        enemy_type: Enemy type key (e.g., "goblin", "skeleton")

    Returns:
        Dict with "gold" (int) and "items" (list[str])
    """
    # Normalize enemy type for lookup
    normalized = enemy_type.lower().strip().replace(" ", "_")

    table = LOOT_TABLES.get(normalized, LOOT_TABLES["unknown_enemy"])

    # Roll gold
    gold = 0
    if table["gold_dice"] != "0d0":
        try:
            gold, _ = roll_dice(table["gold_dice"])
            gold = max(0, gold)
        except ValueError:
            gold = 0

    # Roll items
    items = []
    for _ in range(table["rolls"]):
        item = weighted_random_choice(table["items"])
        if item:
            items.append(item)

    logger.debug(
        "Rolled enemy loot",
        extra={
            "enemy_type": normalized,
            "gold": gold,
            "items": items,
        }
    )

    return {"gold": gold, "items": items}


def roll_combat_loot(defeated_enemies: list[dict]) -> dict:
    """Roll loot for all defeated enemies in combat.

    Args:
        defeated_enemies: List of enemy dicts with "name" field

    Returns:
        Combined loot dict with "gold" (int), "items" (list[str]), "source" (str)
    """
    total_gold = 0
    all_items = []

    for enemy in defeated_enemies:
        enemy_name = enemy.get("name", "unknown")
        # Strip numbering (e.g., "Goblin 1" -> "goblin")
        base_name = enemy_name.split()[0] if enemy_name else "unknown"

        loot = roll_enemy_loot(base_name)
        total_gold += loot["gold"]
        all_items.extend(loot["items"])

    logger.info(
        "Rolled combat loot",
        extra={
            "enemy_count": len(defeated_enemies),
            "total_gold": total_gold,
            "items": all_items,
        }
    )

    return {
        "gold": total_gold,
        "items": all_items,
        "source": "combat_victory",
    }


def get_loot_table(enemy_type: str) -> dict | None:
    """Get loot table for an enemy type.

    Args:
        enemy_type: Enemy type key

    Returns:
        Loot table dict or None if not found
    """
    normalized = enemy_type.lower().strip().replace(" ", "_")
    return LOOT_TABLES.get(normalized)
```

**Validation**:
- [ ] Module imports correctly
- [ ] Loot tables cover all bestiary enemies
- [ ] All loot table items exist in ITEM_CATALOG:
  - dagger ✓
  - rations ✓
  - potion_healing ✓
  - torch ✓
  - rusty_key ✓
  - ancient_scroll ✓
  - sword ✓
  - shield ✓
  - chain_mail ✓
  - golden_key ✓

### Step 2: Add loot_table Field to Bestiary
**Files**: `lambdas/dm/bestiary.py`

Add `loot_table` field to each enemy in BESTIARY.

```python
# Add loot_table field to each entry. Examples:

"goblin": {
    "name": "Goblin",
    "hp_dice": "1d6",
    "ac": 12,
    "attack_bonus": 1,
    "damage_dice": "1d6",
    "xp_value": 10,
    "loot_table": "goblin",  # ADD THIS
},
"skeleton": {
    "name": "Skeleton",
    "hp_dice": "1d8",
    "ac": 13,
    "attack_bonus": 1,
    "damage_dice": "1d6",
    "xp_value": 15,
    "loot_table": "skeleton",  # ADD THIS
},
# ... add to all entries
```

**Validation**:
- [ ] All bestiary entries have loot_table field
- [ ] spawn_enemy() still works correctly

### Step 3: Roll Loot on Combat Victory
**Files**: `lambdas/dm/service.py`

Modify `_end_combat_response()` to roll loot on victory and store in session.

In `_end_combat_response()`, after checking for victory:

```python
# At the start of the method, add import
from shared.loot import roll_combat_loot

# Inside _end_combat_response(), when victory=True:
if victory:
    # Roll loot from defeated enemies
    combat_enemies_data = session.get("combat_enemies", [])
    pending_loot = roll_combat_loot(combat_enemies_data)
    if pending_loot["gold"] > 0 or pending_loot["items"]:
        session["pending_loot"] = pending_loot
        logger.info(
            "Pending loot set",
            extra={"loot": pending_loot}
        )
```

**Validation**:
- [ ] Loot rolled only on victory
- [ ] pending_loot stored in session

### Step 4: Clear Pending Loot on Combat Start
**Files**: `lambdas/dm/service.py`

In `_initiate_combat()`, clear any existing pending_loot.

```python
def _initiate_combat(self, session: dict, enemies: list[Enemy]) -> None:
    # At the start of the method:
    # Clear any unclaimed loot from previous combat
    if session.get("pending_loot"):
        logger.info(
            "Unclaimed loot lost on new combat",
            extra={"loot": session["pending_loot"]}
        )
        session["pending_loot"] = None

    # ... rest of method
```

**Validation**:
- [ ] Old loot cleared when new combat starts
- [ ] Log message shows lost loot

### Step 5: Update DM Prompt with Pending Loot
**Files**: `lambdas/dm/prompts/context.py`

Add pending loot info to DM context when available.

```python
# In build_context() or wherever session context is built:

def build_loot_context(session: dict) -> str:
    """Build context string for pending loot."""
    pending = session.get("pending_loot")
    if not pending:
        return ""

    gold = pending.get("gold", 0)
    items = pending.get("items", [])

    if not gold and not items:
        return ""

    lines = [
        "\n## LOOT AVAILABLE",
        "The player has defeated enemies. Loot is available to claim:",
    ]

    if gold > 0:
        lines.append(f"- Gold: {gold}")

    if items:
        # Convert item IDs to display names
        from shared.items import ITEM_CATALOG
        item_names = []
        for item_id in items:
            if item_id in ITEM_CATALOG:
                item_names.append(ITEM_CATALOG[item_id].name)
            else:
                item_names.append(item_id.replace("_", " ").title())
        lines.append(f"- Items: {', '.join(item_names)}")

    lines.extend([
        "",
        "IMPORTANT: Prompt the player to search the bodies.",
        "Accept variations like: 'search', 'loot', 'check bodies', 'take their stuff'",
        "When player searches, output state changes:",
        f"  gold_delta: +{gold}" if gold else "",
        f"  inventory_add: {items}" if items else "",
        "Do NOT give loot until player explicitly searches.",
        "If player declines, acknowledge their choice - loot remains available.",
    ])

    return "\n".join(lines)
```

**Validation**:
- [ ] Loot context appears in DM prompt when pending
- [ ] Item IDs converted to display names

### Step 6: Handle Loot Claiming
**Files**: `lambdas/dm/service.py`

Modify `_apply_state_changes()` to validate loot claims against pending_loot.

```python
def _apply_state_changes(
    self,
    character: dict,
    session: dict,
    dm_response: DMResponse,
) -> tuple[dict, dict]:
    """Apply state changes from DM response."""
    state = dm_response.state_changes
    pending = session.get("pending_loot")

    # If there's pending loot and DM is giving gold/items, validate
    if pending:
        # Validate gold claim
        if state.gold_delta > 0:
            if state.gold_delta <= pending.get("gold", 0):
                # Valid claim - allow it, reduce pending
                pending["gold"] = pending.get("gold", 0) - state.gold_delta
            else:
                # DM trying to give more gold than available
                logger.warning(
                    "DM tried to give more gold than pending",
                    extra={"requested": state.gold_delta, "available": pending.get("gold", 0)}
                )
                state.gold_delta = pending.get("gold", 0)
                pending["gold"] = 0

        # Validate item claims
        validated_items = []
        pending_items = list(pending.get("items", []))
        for item_name in state.inventory_add:
            # Check if item is in pending loot
            item_def = find_item_by_name(item_name)
            if item_def and item_def.id in pending_items:
                validated_items.append(item_name)
                pending_items.remove(item_def.id)
            elif item_def and item_def.id not in pending_items:
                logger.warning(
                    "DM tried to give item not in pending loot",
                    extra={"item": item_name, "pending": pending_items}
                )
                # Don't add this item
            else:
                # Item not in catalog - already handled by existing validation
                pass

        # Update pending items
        pending["items"] = pending_items
        state.inventory_add = validated_items

        # Clear pending_loot if empty
        if pending.get("gold", 0) <= 0 and not pending.get("items"):
            session["pending_loot"] = None
            logger.info("All pending loot claimed")
        else:
            session["pending_loot"] = pending

    # ... rest of existing _apply_state_changes logic
```

**Validation**:
- [ ] Gold claims validated against pending
- [ ] Item claims validated against pending
- [ ] Pending loot cleared when all claimed

### Step 7: Add Unit Tests
**Files**: `lambdas/tests/test_loot.py`

```python
"""Tests for loot table system."""

import pytest
from unittest.mock import patch

from shared.loot import (
    LOOT_TABLES,
    weighted_random_choice,
    roll_enemy_loot,
    roll_combat_loot,
    get_loot_table,
)


class TestLootTables:
    """Test loot table definitions."""

    def test_all_bestiary_enemies_have_tables(self):
        """Verify all bestiary enemies have loot tables."""
        from dm.bestiary import BESTIARY

        for enemy_type in BESTIARY:
            table = get_loot_table(enemy_type)
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
        assert "gold" in result  # Should use skeleton table, not fail
```

**Validation**:
- [ ] All tests pass
- [ ] Coverage includes edge cases

### Step 8: Run Tests and Deploy
**Files**: N/A

```bash
# Lambda tests
cd lambdas && pytest tests/test_loot.py -v
cd lambdas && pytest --tb=short

# Deploy backend
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip
```

**Validation**:
- [ ] All tests pass
- [ ] Lambda deployed successfully

---

## Testing Requirements

### Unit Tests
- `test_all_bestiary_enemies_have_tables`: Every bestiary enemy has a loot table
- `test_weighted_random_choice`: Weighted selection works correctly
- `test_roll_enemy_loot`: Single enemy loot roll returns valid structure
- `test_roll_combat_loot`: Multiple enemies combine loot correctly
- `test_enemy_numbering_stripped`: "Goblin 1" uses "goblin" table

### Integration Tests
- Combat victory stores pending_loot in session
- DM prompt includes loot context
- Search action gives gold and items
- New combat clears unclaimed loot

### Manual Testing
1. Fight and defeat goblins
2. Verify DM mentions searching bodies
3. Type "search the bodies"
4. Verify gold and/or items received
5. Start new fight without searching
6. Verify old loot lost

---

## Integration Test Plan

### Prerequisites
- Backend deployed with loot tables
- Frontend running
- Browser DevTools open

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Start new game, enter combat with goblin | Combat initiates | ☐ |
| 2 | Defeat the goblin | Victory message, DM asks about searching | ☐ |
| 3 | Type "search the bodies" | Gold and/or items added to inventory | ☐ |
| 4 | Check character status | Gold increased, items visible | ☐ |
| 5 | Enter another combat, defeat enemy | Victory with loot prompt | ☐ |
| 6 | Don't search, start new combat | Old loot should be lost silently | ☐ |
| 7 | Defeat new enemy, search | Only new loot available | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Search with no pending loot | Type "search" outside combat | DM narrates finding nothing | ☐ |
| Double search | Search twice after same combat | Second search finds nothing extra | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] Gold updates correctly in UI
- [ ] Items appear in inventory

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Unknown enemy type | DM created custom enemy | Use "unknown_enemy" fallback table |
| Invalid dice notation | Bad gold_dice in table | Log warning, return 0 gold |
| Missing item in catalog | Loot table references non-existent item | Skip item, log warning |

### Edge Cases
- **Empty loot roll**: All item rolls return None - just give gold
- **No pending loot on search**: Player searches when no loot available - normal narrative
- **Multiple enemies of same type**: Use base type for table lookup, not "Goblin 1"
- **Boss with high rolls**: Multiple items possible - all valid
- **Animal enemies (wolf)**: 0 gold tables - valid

---

## Cost Impact

### Claude API
- No additional AI calls for loot rolling
- Slightly longer context with loot prompt (~50-100 tokens)
- Estimated impact: ~$0.05/month additional

### AWS
- No new resources
- Minimal additional DynamoDB writes (pending_loot field)
- Estimated impact: $0

---

## Open Questions

1. **Should partial looting be supported?** (Take gold but leave items)
   - *Decision*: No, keep simple - all or nothing for MVP. Can add later.

2. **Should loot be visible in UI before searching?**
   - *Decision*: No, follow classic roguelike - must search to reveal.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Well-defined spec with examples |
| Feasibility | 9 | Follows established patterns |
| Completeness | 9 | Covers all core mechanics |
| Alignment | 10 | Pure server authority, minimal cost |
| **Overall** | 9.25 | High confidence |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling covers edge cases
- [x] Cost impact is estimated (~$0)
- [x] Dependencies are listed
- [x] Success criteria are measurable
