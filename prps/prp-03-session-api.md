# PRP-03: Session API

**Created**: 2026-01-01
**Initial**: `initials/init-03-session-api.md`
**Status**: Ready

---

## Overview

### Problem Statement
Players need to create and manage game sessions that link their characters to active gameplay. A session stores the game state including message history, current location, world state, and campaign setting. Without session management, there's no way to persist or resume gameplay.

### Proposed Solution
Implement a Session Lambda with CRUD endpoints following the established handler/service/models pattern. The API will:
- Create sessions linked to existing characters with preset campaign settings
- List sessions with character names joined for better UX
- Retrieve full session details including message history
- Support paginated message history retrieval
- Delete sessions with ownership validation
- Enforce session limits (max 10 per user)

### Success Criteria
- [ ] POST /sessions creates session with valid character and campaign setting
- [ ] POST /sessions returns 404 for non-existent character
- [ ] POST /sessions returns 409 when user has 10+ sessions
- [ ] GET /sessions returns list with character names joined
- [ ] GET /sessions supports character_id filter
- [ ] GET /sessions/{id} returns full session with history
- [ ] GET /sessions/{id}/history supports pagination with cursor
- [ ] DELETE /sessions/{id} removes session
- [ ] All endpoints validate X-User-ID header (401 if invalid)
- [ ] Invalid campaign_setting returns 400
- [ ] Non-existent session returns 404
- [ ] Unit tests pass with >80% coverage

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Session data model, API endpoints
- `docs/DECISIONS.md` - ADR-004 (single-table design), ADR-005 (anonymous sessions)
- `initials/init-03-session-api.md` - Full specification

### Dependencies
- **Required**:
  - init-01-project-foundation (DynamoDB table, Lambda layer, API Gateway) - COMPLETE
  - init-02-character-api (Characters must exist before sessions) - COMPLETE
- **Optional**: None

### Files to Modify/Create
```
lambdas/session/__init__.py        # New - Package init
lambdas/session/handler.py         # New - Lambda handler with routes
lambdas/session/service.py         # New - Business logic
lambdas/session/models.py          # New - Pydantic request/response models
lambdas/shared/campaigns.py        # New - Campaign setting definitions
cdk/stacks/api_stack.py            # Modify - Add session Lambda and routes
lambdas/tests/test_session_service.py   # New - Service unit tests
lambdas/tests/test_session_handler.py   # New - Handler integration tests
```

---

## Technical Specification

### Data Models

**Request Models** (`session/models.py`):
```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class CampaignSetting(str, Enum):
    DEFAULT = "default"
    DARK_FOREST = "dark_forest"
    CURSED_CASTLE = "cursed_castle"
    FORGOTTEN_MINES = "forgotten_mines"

class SessionCreateRequest(BaseModel):
    character_id: str = Field(..., min_length=36, max_length=36)
    campaign_setting: CampaignSetting = CampaignSetting.DEFAULT

    @field_validator("character_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        # Validate UUID v4 format
        import re
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, v.lower()):
            raise ValueError("character_id must be a valid UUID v4")
        return v
```

**Response Models** (`session/models.py`):
```python
class SessionSummary(BaseModel):
    session_id: str
    character_id: str
    character_name: str
    campaign_setting: str
    current_location: str
    created_at: str
    updated_at: str | None

class SessionResponse(BaseModel):
    session_id: str
    character_id: str
    campaign_setting: str
    current_location: str
    world_state: dict
    message_history: list[dict]
    created_at: str
    updated_at: str | None

class MessageHistoryResponse(BaseModel):
    messages: list[dict]
    has_more: bool
    next_cursor: str | None
```

**Campaign Definitions** (`shared/campaigns.py`):
```python
CAMPAIGN_SETTINGS = {
    "default": {
        "name": "Classic Adventure",
        "starting_location": "The Rusty Tankard tavern in Millbrook village",
        "theme": "Classic fantasy, open-ended exploration",
    },
    "dark_forest": {
        "name": "The Dark Forest",
        "starting_location": "The edge of the Dark Forest, where the road ends",
        "theme": "Horror and survival in haunted woods",
    },
    "cursed_castle": {
        "name": "The Cursed Castle",
        "starting_location": "The crumbling gatehouse of Castle Ravenmoor",
        "theme": "Gothic horror with undead threats",
    },
    "forgotten_mines": {
        "name": "The Forgotten Mines",
        "starting_location": "The abandoned entrance to the Deepholm mines",
        "theme": "Dungeon crawl with ancient treasures",
    },
}

def get_starting_location(campaign: str) -> str:
    return CAMPAIGN_SETTINGS.get(campaign, CAMPAIGN_SETTINGS["default"])["starting_location"]

def get_opening_message(campaign: str, character_name: str) -> str:
    """Generate the initial DM message for a campaign."""
    location = get_starting_location(campaign)
    return f"You are {character_name}. {location}. What do you do?"
```

### API Changes

| Method | Path | Request | Response | Status |
|--------|------|---------|----------|--------|
| POST | /sessions | `{character_id, campaign_setting}` | SessionResponse | 201 |
| GET | /sessions | `?character_id=&limit=` | `{sessions: SessionSummary[]}` | 200 |
| GET | /sessions/{sessionId} | - | SessionResponse | 200 |
| GET | /sessions/{sessionId}/history | `?limit=&before=` | MessageHistoryResponse | 200 |
| DELETE | /sessions/{sessionId} | - | - | 204 |

### DynamoDB Access Patterns

| Operation | PK | SK | Notes |
|-----------|----|----|-------|
| Create session | `USER#{user_id}` | `SESS#{session_id}` | Put item |
| Get session | `USER#{user_id}` | `SESS#{session_id}` | Get item |
| List sessions | `USER#{user_id}` | `begins_with(SESS#)` | Query |
| Get character | `USER#{user_id}` | `CHAR#{character_id}` | For validation |
| Delete session | `USER#{user_id}` | `SESS#{session_id}` | Delete item |
| Count sessions | `USER#{user_id}` | `begins_with(SESS#)` | Query with Select=COUNT |

---

## Implementation Steps

### Step 1: Create Campaign Settings Module
**Files**: `lambdas/shared/campaigns.py`

Create the campaign settings definitions with starting locations and themes.

```python
"""Campaign setting definitions for game sessions."""

CAMPAIGN_SETTINGS: dict[str, dict] = {
    "default": {
        "name": "Classic Adventure",
        "starting_location": "The Rusty Tankard tavern in Millbrook village",
        "theme": "Classic fantasy, open-ended exploration",
    },
    # ... other campaigns
}

def get_starting_location(campaign: str) -> str:
    """Get the starting location for a campaign setting."""
    return CAMPAIGN_SETTINGS.get(campaign, CAMPAIGN_SETTINGS["default"])["starting_location"]

def get_opening_message(campaign: str, character_name: str) -> str:
    """Generate the initial DM message for a new session."""
    location = get_starting_location(campaign)
    return f"You are {character_name}. {location}. What do you do?"
```

**Validation**:
- [ ] Module imports without errors
- [ ] All 4 campaign settings defined

### Step 2: Create Session Pydantic Models
**Files**: `lambdas/session/models.py`

Define request and response models for the session API.

- `CampaignSetting` enum with 4 values
- `SessionCreateRequest` with character_id validation
- `SessionSummary` for list responses
- `SessionResponse` for full session data
- `MessageHistoryResponse` for paginated history

**Validation**:
- [ ] Models validate correctly
- [ ] Invalid campaign_setting raises ValidationError

### Step 3: Create Session Service
**Files**: `lambdas/session/service.py`

Implement business logic following the character service pattern:

```python
class SessionService:
    def __init__(self, db_client: DynamoDBClient) -> None:
        self.db = db_client

    def create_session(self, user_id: str, request: SessionCreateRequest) -> dict:
        """Create a new game session."""
        # 1. Verify character exists and belongs to user
        # 2. Count existing sessions (enforce 10 max)
        # 3. Get starting location from campaign
        # 4. Create initial DM message
        # 5. Save session to DynamoDB
        # 6. Return session data

    def list_sessions(self, user_id: str, character_id: str | None = None, limit: int = 20) -> list[dict]:
        """List sessions with character names joined."""
        # 1. Query sessions by user
        # 2. Filter by character_id if provided
        # 3. Batch get character names
        # 4. Return summaries with names

    def get_session(self, user_id: str, session_id: str) -> dict:
        """Get full session details."""

    def get_message_history(self, user_id: str, session_id: str, limit: int = 20, before: str | None = None) -> dict:
        """Get paginated message history."""
        # 1. Get session
        # 2. Filter messages by timestamp if cursor provided
        # 3. Return messages with pagination info

    def delete_session(self, user_id: str, session_id: str) -> None:
        """Delete a session."""
```

**Key Logic**:
- Character validation: Query `USER#{user_id}` / `CHAR#{character_id}`, raise NotFoundError if missing
- Session limit: Query sessions with `Select=COUNT`, raise ConflictError if >= 10
- Message history: Reverse sort by timestamp, slice for pagination

**Validation**:
- [ ] Service methods work with mock DB
- [ ] Character validation works
- [ ] Session limit enforced

### Step 4: Create Session Lambda Handler
**Files**: `lambdas/session/handler.py`, `lambdas/session/__init__.py`

Create handler following the character handler pattern:

```python
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    NotFoundError as APINotFoundError,
    UnauthorizedError,
)

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

@app.post("/sessions")
@tracer.capture_method
def create_session() -> Response:
    """Create a new game session."""
    # Return 201 with session data

@app.get("/sessions")
@tracer.capture_method
def list_sessions() -> dict:
    """List all sessions for user."""
    # Handle optional character_id and limit query params

@app.get("/sessions/<session_id>")
@tracer.capture_method
def get_session(session_id: str) -> dict:
    """Get full session details."""

@app.get("/sessions/<session_id>/history")
@tracer.capture_method
def get_message_history(session_id: str) -> dict:
    """Get paginated message history."""
    # Handle limit and before query params

@app.delete("/sessions/<session_id>")
@tracer.capture_method
def delete_session(session_id: str) -> Response:
    """Delete a session."""
    # Return 204 No Content
```

**Error Handling**:
- `ValidationError` → `BadRequestError` (400)
- `NotFoundError` → `APINotFoundError` (404)
- `ConflictError` → Custom 409 response
- Missing X-User-ID → `UnauthorizedError` (401)

**Validation**:
- [ ] All routes respond correctly
- [ ] Error handling works

### Step 5: Add ConflictError to Shared Exceptions
**Files**: `lambdas/shared/exceptions.py`

Add a new exception for the 409 Conflict case:

```python
class ConflictError(ChaosDungeonError):
    """Raised when an operation conflicts with current state."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
```

**Validation**:
- [ ] Exception can be raised and caught

### Step 6: Update CDK API Stack
**Files**: `cdk/stacks/api_stack.py`

1. Add `_create_session_lambda()` method (following character pattern)
2. Create session Lambda in constructor
3. Replace mock integrations with real Lambda integration
4. Add output for session function ARN

```python
def _create_session_lambda(self) -> lambda_.Function:
    """Create the session handler Lambda function."""
    function = lambda_.Function(
        self,
        "SessionHandler",
        function_name=f"{self.prefix}-session",
        runtime=lambda_.Runtime.PYTHON_3_12,
        handler="session.handler.lambda_handler",
        code=lambda_.Code.from_asset(
            "../lambdas",
            exclude=[...],  # Same excludes as character
        ),
        layers=[self.shared_layer],
        environment={
            "TABLE_NAME": self.base_stack.table.table_name,
            "ENVIRONMENT": self.deploy_env,
            "POWERTOOLS_SERVICE_NAME": "session",
            "POWERTOOLS_LOG_LEVEL": "DEBUG" if self.deploy_env == "dev" else "INFO",
        },
        timeout=Duration.seconds(30),
        memory_size=256,
        tracing=lambda_.Tracing.ACTIVE,
    )
    self.base_stack.table.grant_read_write_data(function)
    return function
```

**Route Changes**:
- Remove mock integrations for `/sessions` endpoints
- Add real Lambda integrations
- Add GET /sessions route (was missing in mocks)

**Validation**:
- [ ] `cdk synth` succeeds
- [ ] No duplicate routes

### Step 7: Write Unit Tests for Session Service
**Files**: `lambdas/tests/test_session_service.py`

Test cases:
- `TestCreateSession`:
  - Creates session with valid character
  - Returns 404 for non-existent character
  - Returns 409 when user has 10 sessions
  - Uses correct campaign starting location
  - Generates opening DM message
- `TestListSessions`:
  - Returns empty list when no sessions
  - Returns sessions with character names
  - Filters by character_id
  - Respects limit parameter
- `TestGetSession`:
  - Returns full session data
  - Returns 404 for non-existent session
  - Strips PK/SK from response
- `TestGetMessageHistory`:
  - Returns messages in reverse chronological order
  - Supports pagination with before cursor
  - Returns has_more flag correctly
- `TestDeleteSession`:
  - Deletes existing session
  - Returns 404 for non-existent session

**Validation**:
- [ ] All tests pass
- [ ] Coverage > 80%

### Step 8: Write Integration Tests for Session Handler
**Files**: `lambdas/tests/test_session_handler.py`

Test cases using moto mock:
- POST /sessions returns 201 with valid data
- POST /sessions returns 400 for invalid campaign_setting
- POST /sessions returns 401 for missing X-User-ID
- POST /sessions returns 404 for non-existent character
- POST /sessions returns 409 when session limit reached
- GET /sessions returns 200 with session list
- GET /sessions returns 200 with empty list
- GET /sessions filters by character_id
- GET /sessions/{id} returns 200 with full session
- GET /sessions/{id} returns 404 for non-existent
- GET /sessions/{id}/history returns paginated messages
- DELETE /sessions/{id} returns 204
- DELETE /sessions/{id} returns 404 for non-existent

**Validation**:
- [ ] All integration tests pass

### Step 9: Run Linters and All Tests
**Commands**:
```bash
cd lambdas
ruff check . --fix
pytest --cov=. --cov-report=term-missing
```

**Validation**:
- [ ] No lint errors
- [ ] All tests pass
- [ ] Coverage > 80%

### Step 10: Update TASK.md and Commit
**Files**: `docs/TASK.md`

Move init-03-session-api.md to Completed section.

**Commit message**:
```
feat: implement session API with CRUD endpoints

- Add Session Lambda with create, list, get, delete endpoints
- Add message history pagination support
- Implement campaign settings (4 preset starting scenarios)
- Enforce session limits (max 10 per user)
- Add comprehensive tests (>80% coverage)
```

---

## Testing Requirements

### Unit Tests
- Session service CRUD operations
- Campaign settings lookup
- Character validation logic
- Session limit enforcement
- Message history pagination

### Integration Tests
- Full endpoint request/response cycles
- Error status codes (400, 401, 404, 409)
- Query parameter handling
- DynamoDB interactions with moto

### Manual Testing
1. Deploy to AWS dev environment
2. Create a character via POST /characters
3. Create a session via POST /sessions with character_id
4. Verify session appears in GET /sessions
5. Retrieve session via GET /sessions/{id}
6. Delete session via DELETE /sessions/{id}
7. Verify 404 on deleted session

---

## Error Handling

### Expected Errors
| Error | HTTP Status | Cause | Handling |
|-------|-------------|-------|----------|
| ValidationError | 400 | Invalid request body | Return validation details |
| UnauthorizedError | 401 | Missing X-User-ID | Return "Missing or invalid X-User-ID" |
| NotFoundError | 404 | Session/character not found | Return "{type} not found" |
| ConflictError | 409 | Session limit exceeded | Return "Maximum 10 sessions allowed" |

### Edge Cases
- Character deleted after session created → Session still accessible (orphaned)
- Empty message history → Return empty list, not error
- Invalid UUID format → 400 with validation error
- Concurrent session creation → May exceed limit briefly (acceptable for MVP)

---

## Cost Impact

### Claude API
- This feature does NOT call Claude API
- Only stores session state for future DM interactions
- Estimated impact: $0

### AWS
- **Lambda**: Negligible (within free tier)
- **DynamoDB**: ~$0.25/month additional
  - Session items: ~2KB each
  - Expected: 100-500 sessions total
  - Reads: ~1000/month ($0.000125)
  - Writes: ~500/month ($0.000625)
- **API Gateway**: Negligible increase
- **Total estimated impact**: < $0.50/month

---

## Open Questions

1. ~~Should sessions auto-delete after 30 days of inactivity?~~ → Future enhancement, not MVP
2. Should we support session "pause" state vs active? → No, all sessions are active for MVP
3. What happens when character is deleted but sessions exist? → Sessions become orphaned (acceptable for MVP)

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements are well-defined in init spec |
| Feasibility | 10 | Follows established patterns from character API |
| Completeness | 9 | All endpoints and edge cases covered |
| Alignment | 10 | Within budget, follows ADRs |
| **Overall** | **9.5** | Ready for implementation |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
