# PRP-02: Character CRUD API

**Created**: 2026-01-01
**Initial**: `initials/init-02-character-api.md`
**Status**: Ready

---

## Overview

### Problem Statement
Players need to create, manage, and delete characters before starting game sessions. The foundation infrastructure (DynamoDB, Lambda layer, API Gateway) is in place, but the character endpoints return mock responses. We need real Lambda handlers that implement BECMI character creation with proper stat rolling and class-based abilities.

### Proposed Solution
Implement a Character Lambda handler that:
1. Processes CRUD operations for characters
2. Generates stats using 3d6 rolls per BECMI rules
3. Calculates HP based on class hit dice + CON modifier
4. Persists characters to DynamoDB using the existing single-table design
5. Validates user identity via X-User-ID header (anonymous sessions per ADR-005)

### Success Criteria
- [ ] POST /characters creates character with rolled stats (3d6) and class-based HP
- [ ] GET /characters returns list of user's characters (summary only)
- [ ] GET /characters/{id} returns full character details
- [ ] PATCH /characters/{id} updates character name
- [ ] DELETE /characters/{id} removes character
- [ ] Invalid user ID returns 401
- [ ] Invalid character class returns 400
- [ ] Non-existent character returns 404
- [ ] Stats are in 3-18 range (3d6)
- [ ] HP respects class HD + CON modifier (minimum 1 HP)
- [ ] Starting gold is 3d6 × 10 (30-180 gp)
- [ ] Unit tests pass with >80% coverage

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview, data models
- `docs/DECISIONS.md` - ADR-004 (single-table design), ADR-005 (anonymous sessions)
- `initials/init-02-character-api.md` - Feature specification

### Dependencies
- **Required**: `init-01-project-foundation` - DynamoDB table, Lambda layer, API Gateway (✅ Complete)
- **Optional**: None

### Files to Modify/Create
```
lambdas/
├── character/
│   ├── __init__.py           # New: Package init
│   ├── handler.py            # New: Lambda entry point with APIGatewayRestResolver
│   ├── service.py            # New: Business logic (create, list, get, update, delete)
│   └── models.py             # New: Request/response Pydantic models
├── shared/
│   ├── becmi.py              # New: BECMI rules (hit dice, starting abilities)
│   └── utils.py              # Modify: Add roll_hit_dice function
├── tests/
│   ├── test_character_handler.py  # New: Handler integration tests
│   ├── test_character_service.py  # New: Service unit tests
│   └── test_becmi.py              # New: BECMI rules unit tests
cdk/
└── stacks/
    └── api_stack.py          # Modify: Replace mock integrations with Lambda
```

---

## Technical Specification

### Data Models

**Request Models (`lambdas/character/models.py`):**
```python
from pydantic import BaseModel, Field, field_validator
import re

class CharacterCreateRequest(BaseModel):
    """Request body for creating a new character."""
    name: str = Field(..., min_length=3, max_length=30)
    character_class: str = Field(..., pattern="^(fighter|thief|magic_user|cleric)$")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9 ]+$", v):
            raise ValueError("Name must be alphanumeric with spaces only")
        return v

class CharacterUpdateRequest(BaseModel):
    """Request body for updating a character."""
    name: str = Field(..., min_length=3, max_length=30)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9 ]+$", v):
            raise ValueError("Name must be alphanumeric with spaces only")
        return v
```

**Response Models (`lambdas/character/models.py`):**
```python
class CharacterSummary(BaseModel):
    """Summary view for character list."""
    character_id: str
    name: str
    character_class: str
    level: int
    created_at: str

class CharacterListResponse(BaseModel):
    """Response for GET /characters."""
    characters: list[CharacterSummary]

class CharacterResponse(BaseModel):
    """Full character response."""
    character_id: str
    name: str
    character_class: str
    level: int
    xp: int
    hp: int
    max_hp: int
    gold: int
    stats: dict[str, int]  # str, int, wis, dex, con, cha
    inventory: list[dict]
    abilities: list[str]
    created_at: str
    updated_at: str
```

**BECMI Rules (`lambdas/shared/becmi.py`):**
```python
from enum import Enum

class CharacterClass(str, Enum):
    FIGHTER = "fighter"
    THIEF = "thief"
    MAGIC_USER = "magic_user"
    CLERIC = "cleric"

# Hit dice by class
HIT_DICE = {
    CharacterClass.FIGHTER: 8,      # 1d8
    CharacterClass.CLERIC: 6,       # 1d6
    CharacterClass.THIEF: 4,        # 1d4
    CharacterClass.MAGIC_USER: 4,   # 1d4
}

# Starting abilities by class
STARTING_ABILITIES = {
    CharacterClass.FIGHTER: ["Attack", "Parry"],
    CharacterClass.THIEF: ["Attack", "Backstab", "Pick Locks", "Hide in Shadows"],
    CharacterClass.MAGIC_USER: ["Attack", "Cast Spell"],
    CharacterClass.CLERIC: ["Attack", "Turn Undead"],
}

def get_hit_dice(character_class: CharacterClass) -> int:
    """Return hit die size for a class."""
    return HIT_DICE[character_class]

def get_starting_abilities(character_class: CharacterClass) -> list[str]:
    """Return starting abilities for a class."""
    return STARTING_ABILITIES[character_class].copy()
```

### API Changes

The API routes already exist in `api_stack.py` with mock integrations. Replace with Lambda integrations:

| Method | Path | Request | Response | Status |
|--------|------|---------|----------|--------|
| POST | /characters | `{name, character_class}` | Full character | 201 |
| GET | /characters | - | `{characters: [...]}` | 200 |
| GET | /characters/{characterId} | - | Full character | 200/404 |
| PATCH | /characters/{characterId} | `{name}` | Full character | 200/404 |
| DELETE | /characters/{characterId} | - | - | 204/404 |

### DynamoDB Access Patterns

Using existing `DynamoDBClient` from `shared/db.py`:

| Operation | Method | PK | SK |
|-----------|--------|----|----|
| Create | `put_item()` | `USER#{user_id}` | `CHAR#{character_id}` |
| List | `query_by_pk()` | `USER#{user_id}` | prefix=`CHAR#` |
| Get | `get_item_or_raise()` | `USER#{user_id}` | `CHAR#{character_id}` |
| Update | `update_item()` | `USER#{user_id}` | `CHAR#{character_id}` |
| Delete | `delete_item()` | `USER#{user_id}` | `CHAR#{character_id}` |

---

## Implementation Steps

### Step 1: Create BECMI Rules Module
**Files**: `lambdas/shared/becmi.py`

Create the BECMI rules module with hit dice definitions, starting abilities, and helper functions.

```python
"""BECMI D&D rules for character generation."""
from enum import Enum
from typing import Dict, List

class CharacterClass(str, Enum):
    FIGHTER = "fighter"
    THIEF = "thief"
    MAGIC_USER = "magic_user"
    CLERIC = "cleric"

HIT_DICE: Dict[CharacterClass, int] = {
    CharacterClass.FIGHTER: 8,
    CharacterClass.CLERIC: 6,
    CharacterClass.THIEF: 4,
    CharacterClass.MAGIC_USER: 4,
}

STARTING_ABILITIES: Dict[CharacterClass, List[str]] = {
    CharacterClass.FIGHTER: ["Attack", "Parry"],
    CharacterClass.THIEF: ["Attack", "Backstab", "Pick Locks", "Hide in Shadows"],
    CharacterClass.MAGIC_USER: ["Attack", "Cast Spell"],
    CharacterClass.CLERIC: ["Attack", "Turn Undead"],
}

def get_hit_dice(character_class: CharacterClass) -> int:
    return HIT_DICE[character_class]

def get_starting_abilities(character_class: CharacterClass) -> list[str]:
    return STARTING_ABILITIES[character_class].copy()

def roll_starting_hp(hit_die: int, con_modifier: int) -> int:
    """Roll starting HP: 1d(hit_die) + CON modifier, minimum 1."""
    from shared.utils import roll_dice
    roll = roll_dice(1, hit_die)
    return max(1, roll + con_modifier)

def roll_starting_gold() -> int:
    """Roll starting gold: 3d6 × 10."""
    from shared.utils import roll_dice
    return roll_dice(3, 6) * 10
```

**Validation**:
- [ ] Unit tests for all functions
- [ ] Ruff lint passes

### Step 2: Add roll_hit_dice to utils.py
**Files**: `lambdas/shared/utils.py`

The `roll_dice()` function already exists. No changes needed - we'll use it from `becmi.py`.

**Validation**:
- [ ] Existing tests still pass

### Step 3: Create Character Request/Response Models
**Files**: `lambdas/character/models.py`

Create Pydantic models for request validation and response serialization.

**Validation**:
- [ ] Unit tests for validation (name format, class enum)
- [ ] Ruff lint passes

### Step 4: Create Character Service
**Files**: `lambdas/character/service.py`

Implement business logic for all CRUD operations. This service layer separates business logic from the Lambda handler.

```python
"""Character service - business logic for character CRUD operations."""
from aws_lambda_powertools import Logger
from shared.db import DynamoDBClient
from shared.becmi import (
    CharacterClass, get_hit_dice, get_starting_abilities,
    roll_starting_hp, roll_starting_gold
)
from shared.utils import (
    generate_id, utc_now, roll_ability_scores, calculate_modifier
)
from shared.exceptions import NotFoundError
from character.models import CharacterCreateRequest, CharacterUpdateRequest

logger = Logger()

class CharacterService:
    def __init__(self, db_client: DynamoDBClient):
        self.db = db_client

    def create_character(self, user_id: str, request: CharacterCreateRequest) -> dict:
        """Create a new character with rolled stats."""
        character_id = generate_id()
        now = utc_now()

        # Roll stats
        stats = roll_ability_scores()
        con_modifier = calculate_modifier(stats["con"])

        # Get class-specific values
        char_class = CharacterClass(request.character_class)
        hit_die = get_hit_dice(char_class)
        hp = roll_starting_hp(hit_die, con_modifier)
        abilities = get_starting_abilities(char_class)
        gold = roll_starting_gold()

        character = {
            "character_id": character_id,
            "name": request.name,
            "character_class": request.character_class,
            "level": 1,
            "xp": 0,
            "hp": hp,
            "max_hp": hp,
            "gold": gold,
            "stats": stats,
            "inventory": [],
            "abilities": abilities,
            "created_at": now,
            "updated_at": now,
        }

        self.db.put_item(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{character_id}",
            attributes=character
        )

        return character

    def list_characters(self, user_id: str) -> list[dict]:
        """List all characters for a user (summary only)."""
        items = self.db.query_by_pk(
            pk=f"USER#{user_id}",
            sk_prefix="CHAR#"
        )
        return [
            {
                "character_id": item["character_id"],
                "name": item["name"],
                "character_class": item["character_class"],
                "level": item["level"],
                "created_at": item["created_at"],
            }
            for item in items
        ]

    def get_character(self, user_id: str, character_id: str) -> dict:
        """Get full character details."""
        try:
            item = self.db.get_item_or_raise(
                pk=f"USER#{user_id}",
                sk=f"CHAR#{character_id}"
            )
            # Remove DynamoDB keys from response
            return {k: v for k, v in item.items() if k not in ("PK", "SK")}
        except NotFoundError:
            raise NotFoundError("Character", character_id)

    def update_character(self, user_id: str, character_id: str,
                         request: CharacterUpdateRequest) -> dict:
        """Update character (name only for now)."""
        # Verify character exists
        self.get_character(user_id, character_id)

        now = utc_now()
        self.db.update_item(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{character_id}",
            updates={"name": request.name, "updated_at": now}
        )

        return self.get_character(user_id, character_id)

    def delete_character(self, user_id: str, character_id: str) -> None:
        """Delete a character."""
        # Verify character exists first
        self.get_character(user_id, character_id)

        self.db.delete_item(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{character_id}"
        )
```

**Validation**:
- [ ] Unit tests for all methods (with mocked DB)
- [ ] Ruff lint passes

### Step 5: Create Character Lambda Handler
**Files**: `lambdas/character/__init__.py`, `lambdas/character/handler.py`

Implement the Lambda handler using APIGatewayRestResolver pattern from examples.

```python
"""Character Lambda handler."""
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError, NotFoundError as APINotFoundError, UnauthorizedError
)
from pydantic import ValidationError

from shared.config import get_config
from shared.db import DynamoDBClient
from shared.utils import extract_user_id, api_response
from shared.exceptions import NotFoundError
from character.service import CharacterService
from character.models import CharacterCreateRequest, CharacterUpdateRequest

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

# Initialize service (lazy)
_service: CharacterService | None = None

def get_service() -> CharacterService:
    global _service
    if _service is None:
        config = get_config()
        db = DynamoDBClient(config.table_name)
        _service = CharacterService(db)
    return _service

def get_user_id() -> str:
    """Extract and validate user ID from headers."""
    user_id = extract_user_id(app.current_event.headers)
    if not user_id:
        raise UnauthorizedError("Missing or invalid X-User-ID header")
    return user_id

@app.post("/characters")
@tracer.capture_method
def create_character():
    """Create a new character."""
    user_id = get_user_id()
    try:
        body = app.current_event.json_body
        request = CharacterCreateRequest(**body)
    except ValidationError as e:
        raise BadRequestError(str(e))

    character = get_service().create_character(user_id, request)
    return api_response(character, status_code=201)

@app.get("/characters")
@tracer.capture_method
def list_characters():
    """List all characters for the current user."""
    user_id = get_user_id()
    characters = get_service().list_characters(user_id)
    return api_response({"characters": characters})

@app.get("/characters/<character_id>")
@tracer.capture_method
def get_character(character_id: str):
    """Get full character details."""
    user_id = get_user_id()
    try:
        character = get_service().get_character(user_id, character_id)
        return api_response(character)
    except NotFoundError:
        raise APINotFoundError("Character not found")

@app.patch("/characters/<character_id>")
@tracer.capture_method
def update_character(character_id: str):
    """Update a character (name only)."""
    user_id = get_user_id()
    try:
        body = app.current_event.json_body
        request = CharacterUpdateRequest(**body)
    except ValidationError as e:
        raise BadRequestError(str(e))

    try:
        character = get_service().update_character(user_id, character_id, request)
        return api_response(character)
    except NotFoundError:
        raise APINotFoundError("Character not found")

@app.delete("/characters/<character_id>")
@tracer.capture_method
def delete_character(character_id: str):
    """Delete a character."""
    user_id = get_user_id()
    try:
        get_service().delete_character(user_id, character_id)
        return api_response(None, status_code=204)
    except NotFoundError:
        raise APINotFoundError("Character not found")

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context) -> dict:
    """Main Lambda entry point."""
    return app.resolve(event, context)
```

**Validation**:
- [ ] Handler routes work correctly
- [ ] Error responses are properly formatted
- [ ] Ruff lint passes

### Step 6: Update CDK to Add Character Lambda
**Files**: `cdk/stacks/api_stack.py`

Replace mock integrations with Lambda integration for character endpoints.

```python
# In api_stack.py, add to __init__:

# Create Character Lambda
self.character_function = self._create_character_lambda(base_stack)

# Replace mock integrations with Lambda integration
character_integration = apigateway.LambdaIntegration(
    self.character_function,
    proxy=True
)

# Update routes to use Lambda integration
characters_resource.add_method("GET", character_integration)
characters_resource.add_method("POST", character_integration)
character_id_resource.add_method("GET", character_integration)
character_id_resource.add_method("PATCH", character_integration)
character_id_resource.add_method("DELETE", character_integration)

def _create_character_lambda(self, base_stack) -> lambda_.Function:
    """Create the character handler Lambda function."""
    return lambda_.Function(
        self, "CharacterHandler",
        function_name=f"chaos-{self.environment}-character",
        runtime=lambda_.Runtime.PYTHON_3_12,
        handler="character.handler.lambda_handler",
        code=lambda_.Code.from_asset("../lambdas"),
        layers=[base_stack.shared_layer],
        environment={
            "TABLE_NAME": base_stack.table.table_name,
            "ENVIRONMENT": self.environment,
            "POWERTOOLS_SERVICE_NAME": "character",
            "POWERTOOLS_LOG_LEVEL": "DEBUG" if self.environment == "dev" else "INFO",
        },
        timeout=Duration.seconds(30),
        memory_size=256,
        tracing=lambda_.Tracing.ACTIVE,
    )

    # Grant DynamoDB access
    base_stack.table.grant_read_write_data(function)

    return function
```

**Validation**:
- [ ] `cdk synth` succeeds
- [ ] `cdk diff` shows expected changes
- [ ] No security warnings

### Step 7: Write Unit Tests for BECMI Module
**Files**: `lambdas/tests/test_becmi.py`

```python
"""Tests for BECMI rules module."""
import pytest
from shared.becmi import (
    CharacterClass, get_hit_dice, get_starting_abilities,
    roll_starting_hp, roll_starting_gold, HIT_DICE, STARTING_ABILITIES
)

class TestHitDice:
    def test_fighter_has_d8(self):
        assert get_hit_dice(CharacterClass.FIGHTER) == 8

    def test_cleric_has_d6(self):
        assert get_hit_dice(CharacterClass.CLERIC) == 6

    def test_thief_has_d4(self):
        assert get_hit_dice(CharacterClass.THIEF) == 4

    def test_magic_user_has_d4(self):
        assert get_hit_dice(CharacterClass.MAGIC_USER) == 4

class TestStartingAbilities:
    def test_fighter_abilities(self):
        abilities = get_starting_abilities(CharacterClass.FIGHTER)
        assert "Attack" in abilities
        assert "Parry" in abilities

    def test_thief_abilities(self):
        abilities = get_starting_abilities(CharacterClass.THIEF)
        assert "Backstab" in abilities
        assert "Pick Locks" in abilities

    def test_abilities_are_copied(self):
        """Ensure we get a copy, not the original list."""
        abilities1 = get_starting_abilities(CharacterClass.FIGHTER)
        abilities2 = get_starting_abilities(CharacterClass.FIGHTER)
        abilities1.append("Test")
        assert "Test" not in abilities2

class TestRollStartingHp:
    def test_hp_minimum_is_one(self):
        """Even with -3 CON modifier, minimum HP is 1."""
        # Run multiple times to catch edge cases
        for _ in range(100):
            hp = roll_starting_hp(4, -3)  # d4 - 3, could be negative
            assert hp >= 1

    def test_hp_includes_modifier(self):
        """HP should include CON modifier."""
        # With +3 modifier, d4 should give 4-7
        results = [roll_starting_hp(4, 3) for _ in range(100)]
        assert min(results) >= 4
        assert max(results) <= 7

class TestRollStartingGold:
    def test_gold_range(self):
        """Starting gold should be 3d6 × 10 = 30-180."""
        for _ in range(100):
            gold = roll_starting_gold()
            assert 30 <= gold <= 180
            assert gold % 10 == 0  # Must be multiple of 10
```

**Validation**:
- [ ] All tests pass
- [ ] Coverage > 90% for becmi.py

### Step 8: Write Unit Tests for Character Service
**Files**: `lambdas/tests/test_character_service.py`

Test the service layer with mocked DynamoDB.

**Validation**:
- [ ] All tests pass
- [ ] Coverage > 80% for service.py

### Step 9: Write Integration Tests for Character Handler
**Files**: `lambdas/tests/test_character_handler.py`

Test the full handler with mocked AWS services.

**Validation**:
- [ ] All endpoints tested
- [ ] Error cases covered (401, 400, 404)
- [ ] Coverage > 80% overall

### Step 10: Deploy and Manual Test
**Commands**:
```bash
cd cdk && cdk deploy --all
```

**Manual Tests**:
1. Create character via API Gateway console or curl
2. List characters
3. Get character by ID
4. Update character name
5. Delete character

**Validation**:
- [ ] All endpoints return expected responses
- [ ] DynamoDB items created correctly
- [ ] CloudWatch logs show proper tracing

---

## Testing Requirements

### Unit Tests

| Test | Description |
|------|-------------|
| `test_becmi.py::TestHitDice` | All classes have correct hit dice |
| `test_becmi.py::TestStartingAbilities` | All classes have correct abilities |
| `test_becmi.py::TestRollStartingHp` | HP calculation with CON modifier, min 1 |
| `test_becmi.py::TestRollStartingGold` | Gold in 30-180 range, multiple of 10 |
| `test_character_service.py::TestCreate` | Character creation with rolled stats |
| `test_character_service.py::TestList` | List returns summaries only |
| `test_character_service.py::TestGet` | Get returns full character |
| `test_character_service.py::TestUpdate` | Update changes name and updated_at |
| `test_character_service.py::TestDelete` | Delete removes character |
| `test_character_models.py::TestValidation` | Name and class validation |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_character_handler.py::test_create_201` | POST returns 201 with character |
| `test_character_handler.py::test_create_400` | Invalid body returns 400 |
| `test_character_handler.py::test_create_401` | Missing user ID returns 401 |
| `test_character_handler.py::test_list_200` | GET returns character list |
| `test_character_handler.py::test_get_200` | GET /{id} returns character |
| `test_character_handler.py::test_get_404` | GET /{id} not found returns 404 |
| `test_character_handler.py::test_update_200` | PATCH updates and returns character |
| `test_character_handler.py::test_delete_204` | DELETE returns 204 |
| `test_character_handler.py::test_delete_404` | DELETE not found returns 404 |

### Manual Testing

1. **Create Character**:
   ```bash
   curl -X POST https://{api-id}.execute-api.{region}.amazonaws.com/dev/characters \
     -H "Content-Type: application/json" \
     -H "X-User-ID: test-user-123" \
     -d '{"name": "Thorin", "character_class": "fighter"}'
   ```
   Expected: 201 with full character, stats in 3-18 range

2. **List Characters**:
   ```bash
   curl https://{api-id}.execute-api.{region}.amazonaws.com/dev/characters \
     -H "X-User-ID: test-user-123"
   ```
   Expected: 200 with characters array (summaries)

3. **Get Character**:
   ```bash
   curl https://{api-id}.execute-api.{region}.amazonaws.com/dev/characters/{id} \
     -H "X-User-ID: test-user-123"
   ```
   Expected: 200 with full character

4. **Delete Character**:
   ```bash
   curl -X DELETE https://{api-id}.execute-api.{region}.amazonaws.com/dev/characters/{id} \
     -H "X-User-ID: test-user-123"
   ```
   Expected: 204 No Content

---

## Error Handling

### Expected Errors

| Error | HTTP | Cause | Handling |
|-------|------|-------|----------|
| UnauthorizedError | 401 | Missing/invalid X-User-ID | Return error message |
| BadRequestError | 400 | Invalid JSON, validation failure | Return validation details |
| NotFoundError | 404 | Character doesn't exist | Return "Character not found" |
| InternalServerError | 500 | DynamoDB failure, unexpected error | Log, return generic message |

### Edge Cases

| Case | Handling |
|------|----------|
| Empty character list | Return `{"characters": []}` |
| Duplicate character names | Allowed - names don't need to be unique |
| Very low CON (-3 modifier) | HP minimum is 1 |
| Maximum stats (all 18s) | Valid, just rare |
| Name with leading/trailing spaces | Trim spaces |
| Special characters in name | Reject with 400 |
| Delete non-existent character | Return 404 |
| User A accessing User B's character | 404 (appears as not found) |

---

## Cost Impact

### Claude API
- **Estimated tokens per request**: 0 (no AI calls in character CRUD)
- **Estimated monthly impact**: $0

### AWS
- **New resources**: 1 Lambda function (character handler)
- **Lambda**: Free tier covers 1M requests/month
- **API Gateway**: ~$0.000001 per request
- **DynamoDB**: ~$1.25 per 1M writes, ~$0.25 per 1M reads
- **Estimated monthly impact**: $0.10-0.50 (negligible within budget)

---

## Open Questions

1. ~~Should we allow stat rerolling?~~ **Resolved**: No, BECMI uses rolled stats as-is
2. ~~Should character names be unique per user?~~ **Resolved**: No, duplicates allowed per spec

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements are well-defined in init spec |
| Feasibility | 10 | Infrastructure already in place, patterns established |
| Completeness | 9 | All CRUD operations covered, tests specified |
| Alignment | 10 | Follows project patterns, within budget |
| **Overall** | **9.5** | High confidence, ready for implementation |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
