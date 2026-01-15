# PRP-18b: Loot Debug and Multi-Word Enemy Fix

**Created**: 2026-01-15
**Initial**: `initials/init-18b-loot-debug.md`
**Status**: Ready

---

## Overview

### Problem Statement
Manual testing revealed that combat loot isn't being claimed when players search bodies. A player defeated a "Drunken Man" enemy, typed "I search the body", and the DM narrated finding coins, but no gold was actually added to inventory.

### Root Causes Identified
1. **Multi-word enemy names broken**: Current code uses `enemy_name.split()[0]` which converts "Drunken Man" to "drunken", missing loot tables
2. **Insufficient logging**: No visibility into loot flow to diagnose issues
3. **Silent failures**: Loot may roll to nothing without any indication

### Proposed Solution
1. Add `LOOT_FLOW:` prefixed diagnostic logging at every step of the loot pipeline
2. Fix multi-word enemy name handling to try full name first, then first word, then fallback
3. Deploy and verify via CloudWatch logs

### Success Criteria
- [ ] `LOOT_FLOW:` logs appear in CloudWatch for combat victory
- [ ] `LOOT_FLOW:` logs show loot being rolled
- [ ] `LOOT_FLOW:` logs show pending_loot stored in session
- [ ] `LOOT_FLOW:` logs show search action detected
- [ ] `LOOT_FLOW:` logs show claim triggered and completed
- [ ] Multi-word enemy names resolve correctly (or fall back to unknown_enemy)
- [ ] After fix: searching body actually adds gold/items to inventory

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview
- `docs/DECISIONS.md` - ADR-012 for validation patterns
- `prps/prp-18-loot-tables.md` - Original loot table implementation
- `prps/prp-18a-item-authority.md` - Item authority lockdown

### Dependencies
- Required: PRP-18a (item authority) - already complete
- Required: PRP-18 (loot tables) - already complete

### Files to Modify
```
lambdas/shared/loot.py       # Add LOOT_FLOW logging, fix multi-word names
lambdas/dm/service.py        # Add LOOT_FLOW logging for victory, search, claim
lambdas/shared/actions.py    # Add LOOT_FLOW logging for search detection
```

---

## Technical Specification

### Log Format
All diagnostic logs use consistent `LOOT_FLOW:` prefix for easy CloudWatch filtering:

```python
logger.info("LOOT_FLOW: <stage>", extra={...})
```

### Expected Log Sequence
```
LOOT_FLOW: Combat victory - enemies: ["Goblin"]
LOOT_FLOW: Enemy table resolution - enemy="Goblin", tried_full="goblin", resolved="goblin"
LOOT_FLOW: Rolled enemy loot - enemy="goblin", gold=3, items=["dagger"]
LOOT_FLOW: Combat loot complete - total_gold=3, items=["dagger"]
LOOT_FLOW: Pending loot stored - pending={gold: 3, items: ["dagger"]}
... player types "search the body" ...
LOOT_FLOW: Search check - action="search the body", is_search=true, has_pending=true
LOOT_FLOW: Triggering claim
LOOT_FLOW: Claim attempt - pending={gold: 3, items: ["dagger"]}, gold_before=0
LOOT_FLOW: Claim complete - gold_added=3, items_added=["dagger"], gold_after=3
```

### Multi-Word Enemy Name Resolution
```python
# Before: "Drunken Man" -> "drunken" (misses tables)
# After: "Drunken Man" -> try "drunken_man" -> try "drunken" -> fallback "unknown_enemy"
```

---

## Implementation Steps

### Step 1: Add LOOT_FLOW Logging to loot.py
**Files**: `lambdas/shared/loot.py`

Add diagnostic logging to `roll_enemy_loot()` and `roll_combat_loot()`:

```python
def roll_enemy_loot(enemy_type: str) -> dict:
    """Roll loot for a single defeated enemy."""
    normalized = enemy_type.lower().strip().replace(" ", "_")

    has_table = normalized in LOOT_TABLES
    table_key = normalized if has_table else "unknown_enemy"

    logger.info("LOOT_FLOW: Enemy table lookup", extra={
        "original": enemy_type,
        "normalized": normalized,
        "has_table": has_table,
        "table_used": table_key,
    })

    table = LOOT_TABLES[table_key]
    # ... rest of function with additional logging ...
```

Fix multi-word name handling in `roll_combat_loot()`:

```python
def roll_combat_loot(defeated_enemies: list[dict]) -> dict:
    for enemy in defeated_enemies:
        enemy_name = enemy.get("name", "unknown")
        # Strip numbering (e.g., "Goblin 1" -> "Goblin")
        base_name = enemy_name.split()[0] if enemy_name else "unknown"

        # Try full name with underscores first (e.g., "drunken_man")
        full_normalized = "_".join(enemy_name.lower().split())
        first_word = base_name.lower()

        if full_normalized in LOOT_TABLES:
            table_key = full_normalized
        elif first_word in LOOT_TABLES:
            table_key = first_word
        else:
            table_key = "unknown_enemy"

        logger.info("LOOT_FLOW: Enemy table resolution", extra={
            "enemy_name": enemy_name,
            "tried_full": full_normalized,
            "tried_first": first_word,
            "resolved_to": table_key,
        })

        loot = roll_enemy_loot(table_key)
        # ...
```

**Validation**:
- [ ] Tests pass
- [ ] Lint passes

### Step 2: Add LOOT_FLOW Logging to service.py (Victory)
**Files**: `lambdas/dm/service.py`

Add logging to combat victory loot roll in `_end_combat_response()`:

```python
if victory:
    combat_enemies_data = session.get("combat_enemies", [])
    logger.info("LOOT_FLOW: Combat victory", extra={
        "enemy_count": len(combat_enemies_data),
        "enemies": [e.get("name") for e in combat_enemies_data],
    })

    pending_loot = roll_combat_loot(combat_enemies_data)

    if pending_loot["gold"] > 0 or pending_loot["items"]:
        session["pending_loot"] = pending_loot
        logger.info("LOOT_FLOW: Pending loot stored", extra={
            "pending": pending_loot,
        })
    else:
        logger.info("LOOT_FLOW: No loot rolled (empty)")
```

**Validation**:
- [ ] Tests pass
- [ ] Lint passes

### Step 3: Add LOOT_FLOW Logging to service.py (Search & Claim)
**Files**: `lambdas/dm/service.py`

Add logging to search detection in `_process_normal_action()`:

```python
# Before claiming
is_search = is_search_action(action)
has_pending = bool(session.get("pending_loot"))

logger.info("LOOT_FLOW: Search check", extra={
    "action": action[:100],
    "is_search": is_search,
    "has_pending_loot": has_pending,
    "pending_loot": session.get("pending_loot"),
})

if is_search and has_pending:
    logger.info("LOOT_FLOW: Triggering claim")
    claimed_loot = self._claim_pending_loot(character, session)
    logger.info("LOOT_FLOW: Claim result", extra={"claimed": claimed_loot})
```

Add logging to `_claim_pending_loot()`:

```python
def _claim_pending_loot(self, character: dict, session: dict) -> dict | None:
    pending = session.get("pending_loot")

    logger.info("LOOT_FLOW: Claim attempt", extra={
        "pending": pending,
        "character_gold_before": character.get("gold", 0),
        "inventory_count_before": len(character.get("inventory", [])),
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

**Validation**:
- [ ] Tests pass
- [ ] Lint passes

### Step 4: Add LOOT_FLOW Logging to actions.py
**Files**: `lambdas/shared/actions.py`

Add logging to `is_search_action()`:

```python
def is_search_action(action: str) -> bool:
    """Detect if player action is attempting to search/loot."""
    action_lower = action.lower()
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, action_lower):
            logger.info("LOOT_FLOW: Search detected", extra={
                "action": action[:100],
                "matched_pattern": pattern,
            })
            return True

    logger.debug("LOOT_FLOW: Not a search action", extra={
        "action": action[:100],
    })
    return False
```

**Validation**:
- [ ] Tests pass
- [ ] Lint passes

### Step 5: Run Tests and Deploy
**Files**: None (deployment)

1. Run all tests: `cd lambdas && pytest`
2. Deploy to production:
   ```bash
   cd lambdas
   zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
   aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip
   ```
3. Bump version to 0.15.1

**Validation**:
- [ ] All tests pass
- [ ] Lambda deployed successfully

---

## Testing Requirements

### Unit Tests
No new tests required - existing tests cover the functionality. The changes are additive logging and a bug fix.

### Integration Tests (CloudWatch)
After deployment, verify logs appear by:
1. Start a game session
2. Enter combat with any enemy
3. Win combat
4. Type "search the body"
5. Check CloudWatch logs for `LOOT_FLOW:`

### Manual Testing
1. Play through combat → victory → search flow
2. Verify CloudWatch shows full `LOOT_FLOW:` sequence
3. Verify gold/items appear in inventory
4. Test with multi-word enemy name (if DM generates one)

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites
- Backend deployed with logging changes
- Browser DevTools open (Console + Network tabs)
- CloudWatch Logs ready to view

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Start new game | Game loads | ☐ |
| 2 | Trigger combat (attack, explore danger) | Combat starts | ☐ |
| 3 | Win combat | Victory message | ☐ |
| 4 | Type "search the body" | DM narrates finding loot | ☐ |
| 5 | Check inventory | Gold/items appeared | ☐ |
| 6 | Check CloudWatch | LOOT_FLOW: entries visible | ☐ |

### CloudWatch Verification
Filter CloudWatch logs with: `"LOOT_FLOW:"`

Expected sequence:
- [ ] `LOOT_FLOW: Combat victory`
- [ ] `LOOT_FLOW: Enemy table resolution`
- [ ] `LOOT_FLOW: Rolled enemy loot`
- [ ] `LOOT_FLOW: Combat loot complete`
- [ ] `LOOT_FLOW: Pending loot stored`
- [ ] `LOOT_FLOW: Search check`
- [ ] `LOOT_FLOW: Triggering claim`
- [ ] `LOOT_FLOW: Claim complete`

### If Logs Missing
| Missing Log | Likely Cause |
|-------------|--------------|
| Combat victory | Combat didn't end via normal victory flow |
| Enemy table resolution | roll_combat_loot not called |
| Pending loot stored | Loot rolled to nothing (valid) or session not saved |
| Search check | _process_normal_action not called |
| Triggering claim | is_search_action returned false |
| Claim complete | pending_loot was already None |

---

## Error Handling

### Expected Errors
None - logging only, no new error scenarios.

### Edge Cases
- Multi-word enemy names with numbers (e.g., "Drunken Man 1") - handled
- Empty enemy list - results in no loot (valid)
- Unknown enemy type - falls back to unknown_enemy table

---

## Cost Impact

### Claude API
- No change - logging only, no additional AI calls

### AWS
- Slight increase in CloudWatch Logs ingestion: ~$0.01/month
- Well within budget

---

## Open Questions

None - this is a focused debug and fix PRP.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Clear problem, clear solution |
| Feasibility | 10 | Simple logging additions |
| Completeness | 9 | Covers all loot flow stages |
| Alignment | 10 | Essential debugging for game integrity |
| **Overall** | 9.75 | High confidence, low risk |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
