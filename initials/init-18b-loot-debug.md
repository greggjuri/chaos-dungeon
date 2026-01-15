# init-18b-loot-debug

## Overview

Debug and fix the loot claim flow. Manual testing revealed that combat loot isn't being claimed even when players search bodies.

## Problem

### Symptoms
- Player defeated "Drunken Man" in combat
- Player typed "I search the body"
- DM narrated finding coins
- No gold actually added to inventory

### Possible Causes

1. **Enemy not in bestiary**: "Drunken Man" isn't a standard enemy - may not trigger loot roll
2. **Combat victory not detected**: Combat may not have ended through normal victory flow
3. **pending_loot never set**: Loot roll may have been skipped
4. **Search not detected**: Search patterns may not have matched
5. **Claim logic failed**: Server-side claim may have errored silently

## Solution: Diagnostic Logging

Add `LOOT_FLOW:` prefixed logging at every step to trace the flow in CloudWatch.

### 1. Combat Victory Loot Roll

In `service.py` where loot is rolled on combat victory:

```python
# After combat ends with victory
logger.info("LOOT_FLOW: Combat victory", extra={
    "enemies": [e.get("name") for e in combat_enemies],
})

pending_loot = roll_combat_loot(combat_enemies)
logger.info("LOOT_FLOW: Loot rolled", extra={
    "pending_loot": pending_loot,
})

session["pending_loot"] = pending_loot
logger.info("LOOT_FLOW: Pending loot stored in session")
```

### 2. Enemy Name Resolution in Loot Tables

In `loot.py` where enemy names are resolved to tables:

```python
def roll_enemy_loot(enemy_type: str) -> dict:
    # Normalize enemy type
    normalized = enemy_type.lower().strip().replace(" ", "_")
    
    # Check if table exists
    has_table = normalized in LOOT_TABLES
    table_used = normalized if has_table else "unknown_enemy"
    
    logger.info("LOOT_FLOW: Enemy loot lookup", extra={
        "original": enemy_type,
        "normalized": normalized,
        "has_table": has_table,
        "table_used": table_used,
    })
    
    table = LOOT_TABLES.get(normalized, LOOT_TABLES["unknown_enemy"])
    # ... rest of function
```

### 3. Search Action Detection

In `service.py` where search actions are detected:

```python
# Before processing action
from shared.actions import is_search_action

is_search = is_search_action(action)
has_pending = bool(session.get("pending_loot"))

logger.info("LOOT_FLOW: Action check", extra={
    "action": action[:100],  # Truncate for logging
    "is_search": is_search,
    "has_pending_loot": has_pending,
    "pending_loot": session.get("pending_loot"),
})
```

### 4. Loot Claim Execution

In `_claim_pending_loot()`:

```python
def _claim_pending_loot(self, character: dict, session: dict) -> dict | None:
    pending = session.get("pending_loot")
    
    logger.info("LOOT_FLOW: Claim attempt", extra={
        "pending": pending,
        "character_gold_before": character.get("gold", 0),
        "character_inventory_before": len(character.get("inventory", [])),
    })
    
    if not pending:
        logger.info("LOOT_FLOW: No pending loot to claim")
        return None
    
    # ... existing claim logic ...
    
    logger.info("LOOT_FLOW: Claim complete", extra={
        "gold_added": gold,
        "items_added": added_items,
        "character_gold_after": character.get("gold", 0),
    })
    
    return {"gold": gold, "items": added_items}
```

### 5. Verify Claim is Called

Ensure the claim is actually being invoked in the action flow:

```python
# In _process_normal_action() or equivalent
if is_search and has_pending:
    logger.info("LOOT_FLOW: Triggering claim")
    claimed = self._claim_pending_loot(character, session)
    logger.info("LOOT_FLOW: Claim result", extra={"claimed": claimed})
```

## Additional Fix: Multi-Word Enemy Names

The current normalization takes only the first word:
```python
base_name = enemy_name.split()[0] if enemy_name else "unknown"
```

"Drunken Man" becomes "drunken" which won't match any table. This should fall back to `unknown_enemy`, but let's verify and make it explicit:

```python
def roll_combat_loot(defeated_enemies: list[dict]) -> dict:
    for enemy in defeated_enemies:
        enemy_name = enemy.get("name", "unknown")
        
        # Try full name first (with underscores), then first word, then fallback
        normalized_full = enemy_name.lower().strip().replace(" ", "_")
        normalized_first = enemy_name.split()[0].lower() if enemy_name else "unknown"
        
        if normalized_full in LOOT_TABLES:
            table_key = normalized_full
        elif normalized_first in LOOT_TABLES:
            table_key = normalized_first
        else:
            table_key = "unknown_enemy"
        
        logger.info("LOOT_FLOW: Enemy table resolution", extra={
            "enemy_name": enemy_name,
            "tried_full": normalized_full,
            "tried_first": normalized_first,
            "resolved_to": table_key,
        })
        
        loot = roll_enemy_loot(table_key)
```

## Files to Modify

```
lambdas/dm/service.py    # Add logging to victory, search detection, claim
lambdas/shared/loot.py   # Add logging to enemy resolution, improve multi-word handling
```

## Acceptance Criteria

- [ ] `LOOT_FLOW:` logs appear in CloudWatch for combat victory
- [ ] `LOOT_FLOW:` logs show loot being rolled
- [ ] `LOOT_FLOW:` logs show pending_loot stored in session
- [ ] `LOOT_FLOW:` logs show search action detected
- [ ] `LOOT_FLOW:` logs show claim triggered and completed
- [ ] Multi-word enemy names resolve correctly (or fall back to unknown_enemy)
- [ ] After fix: searching body actually adds gold/items to inventory

## Testing

### Deploy and Test
1. Deploy updated lambdas
2. Start new game
3. Find and kill any enemy
4. Type "search the body"
5. Check CloudWatch logs for `LOOT_FLOW:` entries
6. Verify gold/items added to inventory

### Expected Log Sequence
```
LOOT_FLOW: Combat victory - enemies: ["Goblin"]
LOOT_FLOW: Enemy table resolution - resolved_to: "goblin"
LOOT_FLOW: Enemy loot lookup - table_used: "goblin"
LOOT_FLOW: Loot rolled - pending_loot: {gold: 3, items: ["dagger"]}
LOOT_FLOW: Pending loot stored in session
... player types "search the body" ...
LOOT_FLOW: Action check - is_search: true, has_pending_loot: true
LOOT_FLOW: Triggering claim
LOOT_FLOW: Claim attempt - pending: {gold: 3, items: ["dagger"]}
LOOT_FLOW: Claim complete - gold_added: 3, items_added: ["dagger"]
```

If any step is missing from logs, we know exactly where the flow breaks.

## Cost Impact

None - logging only, no additional AI calls or storage.

## Notes

This is a diagnostic-first approach. Once we can see the full flow in logs, we can identify and fix the actual bug. The multi-word enemy name fix is included as a likely culprit.
