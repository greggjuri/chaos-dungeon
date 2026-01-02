# PRP-06: Action Handler

**Created**: 2026-01-02
**Initial**: `initials/init-06-action-handler.md`
**Status**: Ready

---

## Overview

### Problem Statement
The game needs a core game loop where players submit actions and receive AI-generated Dungeon Master responses. Currently, we have character/session CRUD and DM prompt building, but no way to actually send player actions to Claude and get back narrative responses with game state changes.

### Proposed Solution
Implement a Lambda handler that:
1. Receives player actions via POST /sessions/{id}/action
2. Loads session and character state from DynamoDB
3. Builds prompts using the existing DMPromptBuilder (init-05)
4. Calls Claude Haiku 3 API with prompt caching for cost savings
5. Parses response to extract narrative and state changes
6. Applies state changes to character and session
7. Returns formatted response to frontend

### Success Criteria
- [ ] POST /sessions/{id}/action returns DM narrative
- [ ] State changes applied to character (HP, gold, XP, inventory)
- [ ] State changes applied to session (location, world_state)
- [ ] Message history updated with player action and DM response
- [ ] Prompt caching enabled and logged (token usage metrics)
- [ ] Claude API errors handled gracefully (429, 503, 500)
- [ ] Malformed JSON response falls back to narrative only
- [ ] Character death (HP=0) ends session
- [ ] Unit tests for service layer (>80% coverage)
- [ ] Integration tests with mocked Claude client
- [ ] Manual test: send action via browser, verify response

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview, API endpoints
- `docs/DECISIONS.md` - ADR-001 (Haiku 3), ADR-006 (Prompt caching)
- [Anthropic Prompt Caching](https://docs.anthropic.com/claude/docs/prompt-caching)

### Dependencies
- **Required**:
  - init-02-character-api (Character model and DynamoDB access)
  - init-03-session-api (Session model, message history)
  - init-05-dm-system-prompt (DMPromptBuilder, parser, models)
- **Optional**: None

### Files to Modify/Create
```
lambdas/dm/handler.py           # NEW: Lambda entry point
lambdas/dm/service.py           # NEW: Business logic
lambdas/dm/claude_client.py     # NEW: Claude API wrapper
lambdas/dm/models.py            # MODIFY: Add ActionRequest/ActionResponse
lambdas/shared/secrets.py       # NEW: SSM Parameter Store helper
lambdas/tests/test_dm_handler.py      # NEW: Handler tests
lambdas/tests/test_dm_service.py      # NEW: Service tests
lambdas/tests/test_claude_client.py   # NEW: Client tests
cdk/stacks/api_stack.py         # MODIFY: Add DM Lambda + route
```

---

## Technical Specification

### Data Models

```python
# lambdas/dm/models.py (additions)

class ActionRequest(BaseModel):
    """Player action request."""
    action: str = Field(..., min_length=1, max_length=500)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        return v.strip()


class CharacterSnapshot(BaseModel):
    """Character state to include in response."""
    hp: int
    max_hp: int
    xp: int
    gold: int
    level: int
    inventory: list[str]


class ActionResponse(BaseModel):
    """Full response to player action."""
    narrative: str
    state_changes: StateChanges
    dice_rolls: list[DiceRoll]
    combat_active: bool
    enemies: list[Enemy]
    character: CharacterSnapshot
    character_dead: bool = False
    session_ended: bool = False
```

### API Changes
| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | /sessions/{session_id}/action | `{"action": "I attack the goblin"}` | `ActionResponse` |

### Error Responses
| Status | Error | Cause |
|--------|-------|-------|
| 400 | "Action is required" | Empty or missing action |
| 400 | "Action too long (max 500 chars)" | Action exceeds limit |
| 400 | "Session has ended" | Session already ended (death) |
| 401 | "User ID required" | Missing X-User-ID header |
| 404 | "Session not found" | Session doesn't exist or wrong user |
| 404 | "Character not found" | Linked character was deleted |
| 429 | "Rate limit exceeded" | Claude API rate limit |
| 500 | "DM unavailable" | Claude API error |
| 503 | "Service temporarily unavailable" | Claude API timeout |

---

## Implementation Steps

### Step 1: Create Secrets Helper
**Files**: `lambdas/shared/secrets.py`

Create a cached helper for retrieving the Claude API key from SSM Parameter Store.

```python
"""SSM Parameter Store helpers."""
import os
from functools import lru_cache

import boto3
from aws_lambda_powertools import Logger

logger = Logger(child=True)

# SSM Parameter name for Claude API key
CLAUDE_API_KEY_PARAM = "/automations/dev/secrets/anthropic_api_key"


@lru_cache(maxsize=1)
def get_claude_api_key() -> str:
    """Retrieve Claude API key from SSM Parameter Store.

    Cached to avoid repeated API calls within same Lambda invocation.
    Uses WithDecryption=True for SecureString parameters.
    """
    param_name = os.environ.get("CLAUDE_API_KEY_PARAM", CLAUDE_API_KEY_PARAM)

    client = boto3.client("ssm")
    response = client.get_parameter(Name=param_name, WithDecryption=True)
    logger.info("Retrieved Claude API key from SSM Parameter Store")
    return response["Parameter"]["Value"]
```

**Validation**:
- [ ] Tests pass with mocked boto3
- [ ] Lint passes

### Step 2: Create Claude Client
**Files**: `lambdas/dm/claude_client.py`

Create a wrapper for the Anthropic API with prompt caching and logging.

```python
"""Claude API client with prompt caching."""
import anthropic
from aws_lambda_powertools import Logger

logger = Logger(child=True)


class ClaudeClient:
    """Wrapper for Claude API with prompt caching."""

    MODEL = "claude-3-haiku-20240307"
    MAX_TOKENS = 1024

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def send_action(
        self,
        system_prompt: str,
        context: str,
        action: str,
    ) -> str:
        """Send player action to Claude, return raw response text.

        Uses prompt caching on system_prompt for cost savings.
        """
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"{context}\n\n[Player Action]: {action}"
                }
            ],
        )

        # Log cache performance and cost metrics
        usage = response.usage
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(usage, "cache_read_input_tokens", 0)

        # Calculate estimated cost
        estimated_cost = (
            (usage.input_tokens * 0.25 / 1_000_000) +
            (usage.output_tokens * 1.25 / 1_000_000) +
            (cache_read * 0.025 / 1_000_000)  # 90% discount
        )

        logger.info(
            "Claude API usage",
            extra={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
                "estimated_cost_usd": round(estimated_cost, 6),
            },
        )

        return response.content[0].text
```

**Validation**:
- [ ] Tests pass with mocked anthropic client
- [ ] Lint passes

### Step 3: Add Request/Response Models
**Files**: `lambdas/dm/models.py`

Add ActionRequest, CharacterSnapshot, and ActionResponse models.

**Validation**:
- [ ] Model validation works (action length, required fields)
- [ ] Lint passes

### Step 4: Create DM Service
**Files**: `lambdas/dm/service.py`

Implement the core business logic for processing player actions.

Key methods:
- `process_action(session_id, user_id, action)` - Main entry point
- `_apply_state_changes(character, session, dm_response)` - Update game state
- `_append_messages(session, action, narrative)` - Update message history
- `_check_character_death(character, session)` - Handle HP=0

```python
"""DM service for processing player actions."""
from datetime import UTC, datetime

from aws_lambda_powertools import Logger

from dm.claude_client import ClaudeClient
from dm.models import ActionResponse, CharacterSnapshot, DMResponse
from dm.parser import parse_dm_response
from dm.prompts import DMPromptBuilder
from shared.db import DynamoDBClient
from shared.exceptions import NotFoundError, GameStateError
from shared.secrets import get_claude_api_key

logger = Logger(child=True)

MAX_MESSAGE_HISTORY = 50


class DMService:
    """Service for processing player actions through Claude."""

    def __init__(self, db: DynamoDBClient, claude_client: ClaudeClient | None = None):
        self.db = db
        self.claude_client = claude_client
        self.prompt_builder = DMPromptBuilder()

    def _get_claude_client(self) -> ClaudeClient:
        """Lazy initialization of Claude client."""
        if self.claude_client is None:
            api_key = get_claude_api_key()
            self.claude_client = ClaudeClient(api_key)
        return self.claude_client

    def process_action(
        self,
        session_id: str,
        user_id: str,
        action: str,
    ) -> ActionResponse:
        """Process a player action and return the DM response.

        Args:
            session_id: Session UUID
            user_id: User UUID
            action: Player action text

        Returns:
            ActionResponse with narrative, state changes, and character state

        Raises:
            NotFoundError: Session or character not found
            GameStateError: Session has ended
        """
        # Load session
        session_pk = f"USER#{user_id}"
        session_sk = f"SESS#{session_id}"
        session = self.db.get_item(session_pk, session_sk)
        if not session:
            raise NotFoundError("session", session_id)

        # Check if session has ended
        if session.get("status") == "ended":
            raise GameStateError(
                "Session has ended",
                current_state=session.get("ended_reason", "unknown")
            )

        # Load character
        character_id = session["character_id"]
        char_pk = f"USER#{user_id}"
        char_sk = f"CHAR#{character_id}"
        character = self.db.get_item(char_pk, char_sk)
        if not character:
            raise NotFoundError("character", character_id)

        logger.info(
            "Processing player action",
            extra={
                "session_id": session_id,
                "character_id": character_id,
                "action_length": len(action),
            },
        )

        # Build prompts
        campaign = session.get("campaign_setting", "default")
        system_prompt = self.prompt_builder.build_system_prompt(campaign)

        # Build character model for context
        from shared.models import Character, AbilityScores, Item
        char_model = Character(
            character_id=character_id,
            user_id=user_id,
            name=character["name"],
            character_class=character["character_class"],
            level=character["level"],
            xp=character["xp"],
            hp=character["hp"],
            max_hp=character["max_hp"],
            gold=character["gold"],
            abilities=AbilityScores(**character["abilities"]),
            inventory=[Item(**item) if isinstance(item, dict) else Item(name=item) for item in character.get("inventory", [])],
        )

        # Build session model for context
        from shared.models import Session, Message
        sess_model = Session(
            session_id=session_id,
            user_id=user_id,
            character_id=character_id,
            campaign_setting=campaign,
            current_location=session.get("current_location", "Unknown"),
            world_state=session.get("world_state", {}),
            message_history=[Message(**m) for m in session.get("message_history", [])],
        )

        context = self.prompt_builder.build_context(char_model, sess_model)
        user_message = self.prompt_builder.build_user_message(action)

        # Call Claude
        client = self._get_claude_client()
        raw_response = client.send_action(system_prompt, context, action)

        # Parse response
        dm_response = parse_dm_response(raw_response)

        # Apply state changes
        character, session = self._apply_state_changes(
            character, session, dm_response
        )

        # Update message history
        session = self._append_messages(session, action, dm_response.narrative)

        # Check for character death
        character_dead = False
        session_ended = False
        if character["hp"] <= 0:
            character_dead = True
            session_ended = True
            session["status"] = "ended"
            session["ended_reason"] = "character_death"
            logger.info(
                "Character died",
                extra={"character_id": character_id, "session_id": session_id},
            )

        # Save updates to DynamoDB
        now = datetime.now(UTC).isoformat()
        character["updated_at"] = now
        session["updated_at"] = now

        self.db.put_item(char_pk, char_sk, {
            k: v for k, v in character.items()
            if k not in ("PK", "SK")
        })
        self.db.put_item(session_pk, session_sk, {
            k: v for k, v in session.items()
            if k not in ("PK", "SK")
        })

        # Build response
        inventory_names = [
            item["name"] if isinstance(item, dict) else item
            for item in character.get("inventory", [])
        ]

        return ActionResponse(
            narrative=dm_response.narrative,
            state_changes=dm_response.state_changes,
            dice_rolls=dm_response.dice_rolls,
            combat_active=dm_response.combat_active,
            enemies=dm_response.enemies,
            character=CharacterSnapshot(
                hp=character["hp"],
                max_hp=character["max_hp"],
                xp=character["xp"],
                gold=character["gold"],
                level=character["level"],
                inventory=inventory_names,
            ),
            character_dead=character_dead,
            session_ended=session_ended,
        )

    def _apply_state_changes(
        self,
        character: dict,
        session: dict,
        dm_response: DMResponse,
    ) -> tuple[dict, dict]:
        """Apply state changes from DM response."""
        state = dm_response.state_changes

        # Update character HP with bounds
        new_hp = character["hp"] + state.hp_delta
        character["hp"] = max(0, min(new_hp, character["max_hp"]))

        # Update gold (can't go negative)
        character["gold"] = max(0, character["gold"] + state.gold_delta)

        # Update XP
        character["xp"] = character["xp"] + state.xp_delta

        # Inventory changes - handle both Item objects and strings
        inventory = character.get("inventory", [])
        inventory_names = [
            item["name"] if isinstance(item, dict) else item
            for item in inventory
        ]

        for item_name in state.inventory_add:
            if item_name not in inventory_names:
                inventory.append({"name": item_name, "quantity": 1, "weight": 0.0})
                inventory_names.append(item_name)

        for item_name in state.inventory_remove:
            # Find and remove item
            inventory = [
                item for item in inventory
                if (item["name"] if isinstance(item, dict) else item) != item_name
            ]

        character["inventory"] = inventory

        # Update session location
        if state.location:
            session["current_location"] = state.location

        # Merge world state flags
        if state.world_state:
            session.setdefault("world_state", {}).update(state.world_state)

        # Track combat state
        session["combat_active"] = dm_response.combat_active
        if dm_response.enemies:
            session["enemies"] = [e.model_dump() for e in dm_response.enemies]
        elif not dm_response.combat_active:
            session["enemies"] = []

        return character, session

    def _append_messages(
        self,
        session: dict,
        action: str,
        narrative: str,
    ) -> dict:
        """Append player action and DM response to message history."""
        now = datetime.now(UTC).isoformat()

        history = session.get("message_history", [])

        history.append({
            "role": "player",
            "content": action,
            "timestamp": now,
        })
        history.append({
            "role": "dm",
            "content": narrative,
            "timestamp": now,
        })

        # Trim to max messages
        if len(history) > MAX_MESSAGE_HISTORY:
            history = history[-MAX_MESSAGE_HISTORY:]

        session["message_history"] = history
        return session
```

**Validation**:
- [ ] Unit tests for apply_state_changes (HP bounds, inventory, location)
- [ ] Unit tests for append_messages (growth, trimming)
- [ ] Integration tests with mocked Claude client
- [ ] Lint passes

### Step 5: Create DM Handler
**Files**: `lambdas/dm/handler.py`

Create the Lambda entry point following existing handler patterns.

```python
"""DM Lambda handler for processing player actions."""
from typing import Any

import anthropic
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (
    APIGatewayRestResolver,
    CORSConfig,
    Response,
)
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    NotFoundError as APINotFoundError,
    UnauthorizedError,
)
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from dm.models import ActionRequest
from dm.service import DMService
from shared.config import get_config
from shared.db import DynamoDBClient
from shared.exceptions import GameStateError, NotFoundError
from shared.utils import extract_user_id

logger = Logger()
tracer = Tracer()

config = get_config()
cors_config = CORSConfig(
    allow_origin="*" if not config.is_production else "https://chaos.jurigregg.com",
    allow_headers=["Content-Type", "X-User-ID", "X-User-Id"],
    allow_methods=["POST", "OPTIONS"],
)
app = APIGatewayRestResolver(cors=cors_config)

_service: DMService | None = None


def get_service() -> DMService:
    """Get or create the DM service singleton."""
    global _service
    if _service is None:
        db = DynamoDBClient(config.table_name)
        _service = DMService(db)
    return _service


def get_user_id() -> str:
    """Extract and validate user ID from request headers."""
    user_id = extract_user_id(app.current_event.headers)
    if not user_id:
        raise UnauthorizedError("User ID required")
    return user_id


@app.post("/sessions/<session_id>/action")
@tracer.capture_method
def post_action(session_id: str) -> Response:
    """Process a player action."""
    user_id = get_user_id()

    try:
        body = app.current_event.json_body or {}
        request = ActionRequest(**body)
    except ValidationError as e:
        error_msg = e.errors()[0].get("msg", "Invalid request")
        raise BadRequestError(error_msg)

    service = get_service()

    try:
        response = service.process_action(
            session_id=session_id,
            user_id=user_id,
            action=request.action,
        )
        return Response(
            status_code=200,
            content_type="application/json",
            body=response.model_dump_json(),
        )
    except NotFoundError as e:
        raise APINotFoundError(f"{e.resource_type.title()} not found")
    except GameStateError as e:
        raise BadRequestError(str(e))
    except anthropic.RateLimitError:
        logger.warning("Claude API rate limit exceeded")
        return Response(
            status_code=429,
            content_type="application/json",
            body='{"error": "Rate limit exceeded. Please try again later."}',
        )
    except anthropic.APIConnectionError as e:
        logger.error(f"Claude API connection error: {e}")
        return Response(
            status_code=503,
            content_type="application/json",
            body='{"error": "Service temporarily unavailable"}',
        )
    except anthropic.APIStatusError as e:
        logger.error(f"Claude API error: {e.status_code} - {e.message}")
        return Response(
            status_code=500,
            content_type="application/json",
            body='{"error": "DM unavailable"}',
        )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Main Lambda entry point."""
    return app.resolve(event, context)
```

**Validation**:
- [ ] Handler tests pass
- [ ] Lint passes

### Step 6: Update CDK Stack
**Files**: `cdk/stacks/api_stack.py`

Add the DM Lambda function and replace the mock integration with real Lambda.

Key changes:
- Create DM Lambda with 30s timeout (Claude can be slow)
- Grant table read/write access
- Grant SSM GetParameter permission for Claude API key parameter
- Replace mock integration with Lambda integration

```python
# Add to DM Lambda environment
"CLAUDE_API_KEY_PARAM": "/automations/dev/secrets/anthropic_api_key",

# Grant SSM parameter read access
from aws_cdk import aws_iam as iam

dm_lambda.add_to_role_policy(
    iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["ssm:GetParameter"],
        resources=["arn:aws:ssm:us-east-1:490004610151:parameter/automations/dev/secrets/anthropic_api_key"],
    )
)
```

**Validation**:
- [ ] `cdk synth` succeeds
- [ ] `cdk diff` shows expected changes

### Step 7: Write Unit Tests
**Files**: `lambdas/tests/test_dm_service.py`, `lambdas/tests/test_dm_handler.py`, `lambdas/tests/test_claude_client.py`, `lambdas/tests/test_secrets.py`

Test cases:
- `test_apply_state_changes_hp_delta` - HP increases/decreases with bounds
- `test_apply_state_changes_hp_at_zero` - HP can't go below 0
- `test_apply_state_changes_hp_at_max` - HP can't exceed max_hp
- `test_apply_state_changes_gold` - Gold changes, can't go negative
- `test_apply_state_changes_xp` - XP accumulates
- `test_apply_state_changes_inventory_add` - Items added
- `test_apply_state_changes_inventory_remove` - Items removed
- `test_apply_state_changes_location` - Location updated
- `test_apply_state_changes_world_state` - World state merged
- `test_append_messages` - Messages appended correctly
- `test_append_messages_trim` - Trims at 50 messages
- `test_process_action_success` - Full flow with mocked Claude
- `test_process_action_session_not_found` - 404 error
- `test_process_action_character_not_found` - 404 error
- `test_process_action_session_ended` - 400 error
- `test_process_action_character_death` - Session ends on HP=0
- `test_claude_client_caching_metrics` - Token usage logged
- `test_handler_post_action_success` - Handler returns 200
- `test_handler_post_action_unauthorized` - Missing user ID returns 401
- `test_handler_post_action_validation_error` - Invalid action returns 400
- `test_handler_rate_limit_error` - Claude rate limit returns 429
- `test_handler_connection_error` - Claude connection error returns 503

**Validation**:
- [ ] All tests pass
- [ ] Coverage > 80%
- [ ] Lint passes

### Step 8: Update Package Exports
**Files**: `lambdas/dm/__init__.py`

Add exports for new modules.

**Validation**:
- [ ] Imports work correctly
- [ ] Lint passes

### Step 9: Add anthropic to requirements
**Files**: `lambdas/requirements.txt`

Add `anthropic>=0.40.0` to requirements.

**Validation**:
- [ ] `pip install -r requirements.txt` succeeds
- [ ] Import works: `python -c "import anthropic"`

### Step 10: Deploy and Integration Test
**Files**: None (deployment and manual testing)

1. Deploy: `cd cdk && cdk deploy --all`
2. Verify Lambda created in AWS Console
3. Test via curl or frontend

**Validation**:
- [ ] Lambda appears in AWS Console
- [ ] API Gateway route configured
- [ ] CloudWatch logs show requests

---

## Testing Requirements

### Unit Tests
- State change application (HP, gold, XP, inventory, location, world_state)
- Message history management (append, trim)
- Character death detection
- Handler error responses (400, 401, 404, 429, 500, 503)
- Claude client token logging

### Integration Tests
- Full action flow with mocked Claude client
- Error handling for missing session/character
- Session ended state handling
- Malformed Claude response fallback

### Manual Testing
1. Create character via API or frontend
2. Create session via API or frontend
3. Send action: "I look around"
4. Verify narrative response
5. Send action: "I search for treasure"
6. Verify state changes in response
7. Check DynamoDB for updated session/character

---

## Integration Test Plan

Manual tests to perform after deployment:

### Prerequisites
- Backend deployed: `cd cdk && cdk deploy --all`
- Claude API key configured in SSM Parameter Store: `/automations/dev/secrets/anthropic_api_key`
- Frontend running: `cd frontend && npm run dev`
- Browser DevTools open (Console + Network tabs)

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Create new character | Character appears in response | ☐ |
| 2 | Start new session | Session created with opening message | ☐ |
| 3 | Send action "I look around" | Receive DM narrative describing surroundings | ☐ |
| 4 | Send action "I search the room" | Receive narrative + possible state changes | ☐ |
| 5 | Check Network tab | POST /sessions/{id}/action returns 200 | ☐ |
| 6 | Check response body | Contains narrative, state_changes, character snapshot | ☐ |
| 7 | Send combat action "I attack" | Receive narrative with dice_rolls array | ☐ |
| 8 | Verify token logging | CloudWatch shows input/output/cache tokens | ☐ |

### Error Scenarios
| Scenario | How to Trigger | Expected Behavior | Pass? |
|----------|----------------|-------------------|-------|
| Missing X-User-ID | Remove header from request | 401 Unauthorized | ☐ |
| Invalid session ID | Use random UUID | 404 Session not found | ☐ |
| Empty action | Send `{"action": ""}` | 400 validation error | ☐ |
| Action too long | Send >500 chars | 400 validation error | ☐ |

### Browser Checks
- [ ] No CORS errors in Console
- [ ] No JavaScript errors in Console
- [ ] API requests visible in Network tab
- [ ] Responses are 2xx (not 4xx/5xx)
- [ ] Response contains valid JSON

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| NotFoundError | Session/character not found | Return 404 |
| GameStateError | Session has ended | Return 400 |
| ValidationError | Invalid action | Return 400 |
| UnauthorizedError | Missing user ID | Return 401 |
| RateLimitError | Claude rate limit | Return 429 |
| APIConnectionError | Claude timeout | Return 503 |
| APIStatusError | Claude API error | Return 500 |

### Edge Cases
- **Malformed JSON in Claude response**: Use narrative only, empty state_changes
- **Character HP reaches 0**: Set session status="ended", ended_reason="character_death"
- **Message history exceeds 50**: Trim oldest messages
- **Inventory already contains item**: Don't add duplicate
- **Item to remove not in inventory**: Skip silently

---

## Cost Impact

### Claude API
- Estimated tokens per request:
  - System prompt: ~2000 (cached after first request)
  - Context: ~500
  - Action: ~50
  - Response: ~500
- Uncached request: ~$0.0015
- Cached request: ~$0.0006 (60% savings)
- Estimated monthly (5000 actions): $3-5

### AWS
- New resources:
  - DM Lambda (256 MB, 30s timeout)
  - CloudWatch logs
- Estimated monthly impact: <$1

---

## Open Questions

1. ~~Rate limiting per user?~~ - Deferred to future iteration
2. ~~Streaming responses?~~ - Out of scope per init-06

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Requirements are very detailed in init-06 |
| Feasibility | 9 | All dependencies exist, patterns established |
| Completeness | 9 | Covers all aspects; streaming deferred |
| Alignment | 10 | Follows budget constraints, uses Haiku 3 |
| **Overall** | **9.5** | High confidence, ready for implementation |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
