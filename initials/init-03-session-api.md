# init-03-session-api

## Overview

Session management API endpoints for creating, listing, retrieving, and deleting game sessions. A session links a character to an active game, storing message history, current location, and world state. This spec covers CRUD operations only—the action handler (sending player actions to the DM) is covered in init-06.

## Dependencies

- init-01-project-foundation (DynamoDB table, Lambda layer, API Gateway)
- init-02-character-api (Characters must exist before sessions)

## API Endpoints

### POST /sessions
Start a new game session with a character.

**Request Body:**
```json
{
  "character_id": "uuid",
  "campaign_setting": "default | dark_forest | cursed_castle | forgotten_mines"
}
```

**Response (201 Created):**
```json
{
  "session_id": "uuid",
  "character_id": "uuid",
  "campaign_setting": "dark_forest",
  "current_location": "The edge of the Dark Forest",
  "world_state": {},
  "message_history": [
    {
      "role": "dm",
      "content": "You stand at the edge of the Dark Forest...",
      "timestamp": "ISO8601"
    }
  ],
  "created_at": "ISO8601",
  "updated_at": null
}
```

**Error Responses:**
- 400: Invalid character_id format, invalid campaign_setting
- 401: Missing/invalid X-User-ID
- 404: Character not found or doesn't belong to user

### GET /sessions
List all sessions for the current user.

**Query Parameters:**
- `character_id` (optional): Filter sessions by character
- `limit` (optional): Max results, default 20, max 50

**Response (200 OK):**
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "character_id": "uuid",
      "character_name": "Grimjaw",
      "campaign_setting": "dark_forest",
      "current_location": "Abandoned Chapel",
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ]
}
```

### GET /sessions/{session_id}
Get full session details including message history.

**Response (200 OK):** Full session object (same as POST response)

**Response (404 Not Found):**
```json
{ "error": "Session not found" }
```

### GET /sessions/{session_id}/history
Get paginated message history.

**Query Parameters:**
- `limit` (optional): Messages to return, default 20, max 100
- `before` (optional): Timestamp cursor for pagination

**Response (200 OK):**
```json
{
  "messages": [
    {
      "role": "dm",
      "content": "The goblin lunges at you with a rusty blade!",
      "timestamp": "ISO8601"
    },
    {
      "role": "player",
      "content": "I dodge and counter-attack with my sword",
      "timestamp": "ISO8601"
    }
  ],
  "has_more": true,
  "next_cursor": "ISO8601"
}
```

### DELETE /sessions/{session_id}
Delete a session permanently.

**Response (204 No Content)**

**Response (404 Not Found):**
```json
{ "error": "Session not found" }
```

## Data Model

**DynamoDB Item:**
```
PK: USER#{user_id}
SK: SESS#{session_id}
```

| Attribute | Type | Notes |
|-----------|------|-------|
| session_id | string (UUID) | Generated on create |
| character_id | string (UUID) | Reference to character |
| campaign_setting | string | Enum (see below) |
| current_location | string | Descriptive location name |
| world_state | map | Flags like `{"dragon_slain": true}` |
| message_history | list[Message] | Capped at last 50 messages |
| created_at | string | ISO8601 |
| updated_at | string | ISO8601, null initially |

### Message Structure
```json
{
  "role": "player | dm",
  "content": "string",
  "timestamp": "ISO8601"
}
```

## Campaign Settings (Preset Starting Scenarios)

For MVP, offer four preset starting scenarios. Each provides an initial location and opening DM narrative:

| Setting | Starting Location | Theme |
|---------|------------------|-------|
| `default` | Village tavern | Classic fantasy, open-ended |
| `dark_forest` | Edge of haunted woods | Horror, survival |
| `cursed_castle` | Castle gatehouse | Gothic, undead |
| `forgotten_mines` | Mine entrance | Dungeon crawl, treasure |

**Note**: Starting narrative text will be defined in init-05-dm-system-prompt. This API just stores the setting choice and initial location.

## Session Limits

Per user constraints (to control DynamoDB costs):
- Maximum 10 active sessions per user
- Maximum 50 messages stored per session (older messages trimmed on new additions)
- Sessions with no activity for 30 days can be auto-deleted (future enhancement)

## User ID Handling

Per ADR-005, use anonymous sessions:
- User ID passed via `X-User-ID` header
- Lambda validates UUID format
- User can only access their own sessions

## Character Validation

When creating a session:
1. Verify character_id is valid UUID format
2. Query DynamoDB for character with `PK=USER#{user_id}`, `SK=CHAR#{character_id}`
3. Return 404 if character doesn't exist or belongs to different user

## Validation Rules

1. **character_id**: Valid UUID v4, must exist and belong to user
2. **campaign_setting**: Must be one of: default, dark_forest, cursed_castle, forgotten_mines
3. **X-User-ID**: Valid UUID v4 format
4. **limit**: Integer 1-50 for sessions, 1-100 for history

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
| 400 | Invalid request body, validation failure |
| 401 | Missing or invalid X-User-ID header |
| 404 | Session or character not found |
| 409 | Session limit exceeded (10 max) |
| 500 | Internal server error |

## Implementation Notes

1. **Pydantic Models**: Create `SessionCreate`, `SessionSummary`, `SessionResponse`, `MessageHistoryResponse`
2. **Character lookup**: Join character name into session list response for better UX
3. **Message trimming**: When message_history exceeds 50, remove oldest messages
4. **Tests Required**:
   - Unit tests for session service
   - Integration tests for each endpoint
   - Edge cases: non-existent character, session limit, empty history

## File Structure

```
lambdas/
├── session/
│   ├── __init__.py
│   ├── handler.py         # Lambda entry point, routes to handlers
│   ├── service.py         # Business logic (create, list, get, delete, history)
│   └── models.py          # Pydantic request/response models
├── shared/
│   └── campaigns.py       # Campaign setting definitions (locations, themes)
```

## CDK Changes

1. Add Lambda function for session handler
2. Add API Gateway routes:
   - POST /sessions → session_handler
   - GET /sessions → session_handler
   - GET /sessions/{session_id} → session_handler
   - GET /sessions/{session_id}/history → session_handler
   - DELETE /sessions/{session_id} → session_handler
3. Grant DynamoDB read/write to session Lambda

## Acceptance Criteria

- [ ] POST /sessions creates session with valid character
- [ ] POST /sessions returns 404 for non-existent character
- [ ] POST /sessions returns 409 when user has 10+ sessions
- [ ] GET /sessions returns list with character names joined
- [ ] GET /sessions supports character_id filter
- [ ] GET /sessions/{id} returns full session with history
- [ ] GET /sessions/{id}/history supports pagination
- [ ] DELETE /sessions/{id} removes session
- [ ] Invalid user ID returns 401
- [ ] Invalid campaign_setting returns 400
- [ ] Non-existent session returns 404
- [ ] Unit tests pass with >80% coverage
