# init-02-character-api

## Overview

Character CRUD API endpoints for creating, listing, retrieving, updating, and deleting player characters. Implements BECMI character creation with 3d6 stat generation.

## Dependencies

- init-01-project-foundation (DynamoDB table, Lambda layer, API Gateway)

## API Endpoints

### POST /characters
Create a new character.

**Request Body:**
```json
{
  "name": "string (3-30 chars, alphanumeric + spaces)",
  "character_class": "fighter | thief | magic_user | cleric"
}
```

**Response (201 Created):**
```json
{
  "character_id": "uuid",
  "name": "string",
  "character_class": "string",
  "level": 1,
  "xp": 0,
  "hp": 8,
  "max_hp": 8,
  "gold": 30,
  "stats": {
    "str": 12, "int": 10, "wis": 9,
    "dex": 14, "con": 11, "cha": 8
  },
  "inventory": [],
  "abilities": ["Attack"],
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### GET /characters
List all characters for the current user.

**Response (200 OK):**
```json
{
  "characters": [
    {
      "character_id": "uuid",
      "name": "string",
      "character_class": "string",
      "level": 1,
      "created_at": "ISO8601"
    }
  ]
}
```

### GET /characters/{character_id}
Get full character details.

**Response (200 OK):** Full character object (same as POST response)

**Response (404 Not Found):**
```json
{ "error": "Character not found" }
```

### PATCH /characters/{character_id}
Update character (rename only for now).

**Request Body:**
```json
{
  "name": "string (3-30 chars, alphanumeric + spaces)"
}
```

**Response (200 OK):** Full updated character object

**Response (404 Not Found):**
```json
{ "error": "Character not found" }
```

### DELETE /characters/{character_id}
Delete a character.

**Response (204 No Content)**

**Response (404 Not Found):**
```json
{ "error": "Character not found" }
```

## Data Model

**DynamoDB Item:**
```
PK: USER#{user_id}
SK: CHAR#{character_id}
```

| Attribute | Type | Notes |
|-----------|------|-------|
| character_id | string (UUID) | Generated on create |
| name | string | Validated 3-30 chars, duplicates allowed |
| character_class | string | Enum: fighter, thief, magic_user, cleric |
| level | number | Starts at 1 |
| xp | number | Starts at 0 |
| hp | number | Current HP |
| max_hp | number | Class-based (see below) |
| gold | number | Starting gold: 3d6 × 10 |
| stats | map | Six abilities, each 3-18 |
| inventory | list | Empty initially |
| abilities | list[string] | Class-based starting abilities |
| created_at | string | ISO8601 |
| updated_at | string | ISO8601 |

## BECMI Character Generation Rules

### Hit Dice by Class (Level 1)
| Class | HD | Average HP |
|-------|-------|-----|
| Fighter | 1d8 | 4-8 |
| Cleric | 1d6 | 3-6 |
| Thief | 1d4 | 2-4 |
| Magic-User | 1d4 | 2-4 |

**HP Calculation:** Roll HD + CON modifier (min 1 HP)

### Stat Generation
Roll 3d6 for each stat in order: STR, INT, WIS, DEX, CON, CHA

### Stat Modifiers (BECMI)
| Score | Modifier |
|-------|----------|
| 3 | -3 |
| 4-5 | -2 |
| 6-8 | -1 |
| 9-12 | 0 |
| 13-15 | +1 |
| 16-17 | +2 |
| 18 | +3 |

### Starting Abilities by Class
| Class | Abilities |
|-------|-----------|
| Fighter | Attack, Parry |
| Thief | Attack, Backstab, Pick Locks, Hide in Shadows |
| Magic-User | Attack, Cast Spell (Read Magic, 1 random 1st-level) |
| Cleric | Attack, Turn Undead, Cast Spell (none at level 1) |

### Starting Gold
3d6 × 10 gold pieces (30-180 gp)

## User ID Handling

Per ADR-005, use anonymous sessions:
- User ID passed via `X-User-ID` header
- Frontend generates UUID on first visit, stores in localStorage
- Lambda validates UUID format (reject invalid)

## Validation Rules

1. **name**: 3-30 characters, alphanumeric + spaces, no leading/trailing spaces, duplicates allowed
2. **character_class**: Must be one of: fighter, thief, magic_user, cleric
3. **X-User-ID**: Valid UUID v4 format

## Error Responses

All errors return JSON:
```json
{
  "error": "string",
  "details": {} // optional validation details
}
```

| Status | Scenario |
|--------|----------|
| 400 | Invalid request body, missing fields, validation failure |
| 401 | Missing or invalid X-User-ID header |
| 404 | Character not found |
| 500 | Internal server error |

## Implementation Notes

1. **Pydantic Models**: Create `CharacterCreate`, `CharacterUpdate`, `Character`, `CharacterSummary`
2. **Dice Module**: Add `roll_dice(count, sides)` to shared utils
3. **BECMI Module**: Add stat modifier calculation, HP calculation
4. **Tests Required**: 
   - Unit tests for dice rolling
   - Unit tests for stat modifiers
   - Integration tests for each endpoint
   - Edge cases: duplicate names, empty character list

## File Structure

```
lambdas/
├── character/
│   ├── __init__.py
│   ├── handler.py         # Lambda entry point, routes to handlers
│   ├── create.py          # POST /characters
│   ├── list.py            # GET /characters
│   ├── get.py             # GET /characters/{id}
│   ├── update.py          # PATCH /characters/{id}
│   ├── delete.py          # DELETE /characters/{id}
│   └── models.py          # Pydantic models
├── shared/
│   ├── __init__.py
│   ├── db.py              # DynamoDB helpers
│   ├── dice.py            # Dice rolling utilities
│   ├── becmi.py           # BECMI rules (modifiers, HP, etc.)
│   └── models.py          # Shared Pydantic models
```

## CDK Changes

1. Add Lambda function for character handler
2. Add API Gateway routes:
   - POST /characters → character_handler
   - GET /characters → character_handler
   - GET /characters/{character_id} → character_handler
   - PATCH /characters/{character_id} → character_handler
   - DELETE /characters/{character_id} → character_handler
3. Grant DynamoDB read/write to character Lambda

## Acceptance Criteria

- [ ] POST /characters creates character with rolled stats and HP
- [ ] GET /characters returns list of user's characters (summary only)
- [ ] GET /characters/{id} returns full character details
- [ ] PATCH /characters/{id} updates character name
- [ ] DELETE /characters/{id} removes character
- [ ] Invalid user ID returns 401
- [ ] Invalid character class returns 400
- [ ] Non-existent character returns 404
- [ ] Stats are 3-18 range (3d6)
- [ ] HP respects class HD + CON modifier
- [ ] Duplicate character names are allowed
- [ ] Unit tests pass with >80% coverage
