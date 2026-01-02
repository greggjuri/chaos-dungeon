# init-06-action-handler

## Overview

Implement the action handler Lambda that processes player actions through Claude Haiku. This is the core game loop: player submits action → Lambda calls Claude API with DM prompts → response parsed → state updated → DM narrative returned. Optimized for cost via prompt caching (ADR-006).

## Dependencies

- init-02-character-api (Character model and DynamoDB access)
- init-03-session-api (Session model, message history)
- init-05-dm-system-prompt (DMPromptBuilder, response parser, models)
- ADR-001 (Claude Haiku 3)
- ADR-006 (Prompt caching)

## API Endpoint

### POST /sessions/{session_id}/action

Submit a player action and receive the DM's response.

**Request Body:**
```json
{
  "action": "I attack the goblin with my sword"
}
```

**Request Headers:**
- `X-User-ID`: UUID (required)

**Response (200 OK):**
```json
{
  "narrative": "You swing your sword in a brutal arc...",
  "state_changes": {
    "hp_delta": -3,
    "gold_delta": 0,
    "xp_delta": 25,
    "location": null,
    "inventory_add": ["rusty key"],
    "inventory_remove": [],
    "world_state": {"goblin_chief_dead": true}
  },
  "dice_rolls": [
    {"type": "attack", "roll": 17, "modifier": 2, "total": 19, "success": true},
    {"type": "damage", "roll": 6, "modifier": 1, "total": 7}
  ],
  "combat_active": false,
  "enemies": [],
  "character": {
    "hp": 5,
    "max_hp": 8,
    "xp": 125,
    "gold": 45,
    "inventory": ["sword", "torch", "rusty key"]
  }
}
```

**Error Responses:**

| Status | Error | Cause |
|--------|-------|-------|
| 400 | "Action is required" | Empty or missing action |
| 400 | "Action too long" | Action exceeds 500 characters |
| 401 | "User ID required" | Missing X-User-ID header |
| 404 | "Session not found" | Session doesn't exist or wrong user |
| 404 | "Character not found" | Linked character was deleted |
| 429 | "Rate limit exceeded" | Too many requests (future) |
| 500 | "DM unavailable" | Claude API error |
| 503 | "Service temporarily unavailable" | Claude API timeout |

## Request Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Lambda    │────▶│  DynamoDB   │
│  POST /action│     │   Handler   │     │ Load session│
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Build Prompt│
                    │ (init-05)   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Claude API  │
                    │  (Haiku 3)  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Parse Response│
                    │  (init-05)  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │Apply State  │────▶│  DynamoDB   │
                    │  Changes    │     │Update session│
                    └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Return     │
                    │  Response   │
                    └─────────────┘
```

## Implementation Details

### Lambda Handler Structure

```
lambdas/
├── dm/
│   ├── __init__.py          # Existing
│   ├── handler.py           # NEW: Lambda entry point
│   ├── service.py           # NEW: Business logic
│   ├── claude_client.py     # NEW: Claude API wrapper
│   ├── models.py            # Existing (add ActionRequest/Response)
│   ├── parser.py            # Existing
│   └── prompts/             # Existing
```

### Claude API Integration

```python
# lambdas/dm/claude_client.py

import anthropic
from aws_lambda_powertools import Logger

logger = Logger()

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
        
        # Log cache performance
        usage = response.usage
        logger.info("Claude API usage", extra={
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
        })
        
        return response.content[0].text
```

### State Change Application

After parsing the DM response, apply state changes to character and session:

```python
def apply_state_changes(
    character: dict,
    session: dict,
    state_changes: StateChanges,
    dm_response: DMResponse,
) -> tuple[dict, dict]:
    """Apply state changes from DM response to character and session."""
    
    # Update character
    character["hp"] = max(0, min(
        character["hp"] + state_changes.hp_delta,
        character["max_hp"]
    ))
    character["gold"] = max(0, character["gold"] + state_changes.gold_delta)
    character["xp"] += state_changes.xp_delta
    
    # Inventory changes
    for item in state_changes.inventory_add:
        if item not in character["inventory"]:
            character["inventory"].append(item)
    for item in state_changes.inventory_remove:
        if item in character["inventory"]:
            character["inventory"].remove(item)
    
    # Update session
    if state_changes.location:
        session["current_location"] = state_changes.location
    
    # Merge world state flags
    session["world_state"].update(state_changes.world_state)
    
    # Track combat state (for future init-09)
    session["combat_active"] = dm_response.combat_active
    if dm_response.enemies:
        session["enemies"] = [e.model_dump() for e in dm_response.enemies]
    elif not dm_response.combat_active:
        session["enemies"] = []
    
    return character, session
```

### Message History Management

```python
def append_messages(
    session: dict,
    player_action: str,
    dm_narrative: str,
) -> dict:
    """Append player action and DM response to message history.
    
    Trims to last 50 messages per init-03 spec.
    """
    now = datetime.utcnow().isoformat() + "Z"
    
    session["message_history"].append({
        "role": "player",
        "content": player_action,
        "timestamp": now,
    })
    session["message_history"].append({
        "role": "dm", 
        "content": dm_narrative,
        "timestamp": now,
    })
    
    # Trim to last 50 messages
    if len(session["message_history"]) > 50:
        session["message_history"] = session["message_history"][-50:]
    
    session["updated_at"] = now
    
    return session
```

### API Key Management

Store Claude API key in AWS Secrets Manager (already provisioned in init-01):

```python
# lambdas/shared/secrets.py

import boto3
from functools import lru_cache

@lru_cache(maxsize=1)
def get_claude_api_key() -> str:
    """Retrieve Claude API key from Secrets Manager.
    
    Cached to avoid repeated API calls within same Lambda invocation.
    """
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="chaos-dungeon/claude-api-key")
    return response["SecretString"]
```

### CDK Changes

Add the DM Lambda to the API stack:

```python
# cdk/stacks/api_stack.py

# DM Lambda (action handler)
dm_lambda = lambda_.Function(
    self, "DMLambda",
    function_name="chaos-dungeon-dm",
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="dm.handler.handler",
    code=lambda_.Code.from_asset("../lambdas"),
    layers=[powertools_layer],
    environment={
        "TABLE_NAME": table.table_name,
        "POWERTOOLS_SERVICE_NAME": "chaos-dungeon-dm",
    },
    timeout=Duration.seconds(30),  # Claude can be slow
    memory_size=256,
)

# Grant permissions
table.grant_read_write_data(dm_lambda)
secrets_manager.Secret.from_secret_name_v2(
    self, "ClaudeApiKey", "chaos-dungeon/claude-api-key"
).grant_read(dm_lambda)

# API route
api.add_routes(
    path="/sessions/{session_id}/action",
    methods=[HttpMethod.POST],
    integration=HttpLambdaIntegration("DmIntegration", dm_lambda),
)
```

## Validation Rules

1. **action**: Required, 1-500 characters, trimmed
2. **session_id**: Valid UUID, must exist and belong to user
3. **Character**: Must still exist (not deleted since session created)

## Error Handling

### Claude API Errors

| Error Type | Handling |
|------------|----------|
| `anthropic.RateLimitError` | Return 429, log warning |
| `anthropic.APIConnectionError` | Return 503, log error |
| `anthropic.APIStatusError` | Return 500, log error with status |
| Timeout (>25s) | Return 503, log timeout |
| Malformed response | Use narrative only, log warning |

### Graceful Degradation

If Claude returns a response without valid JSON:
1. Extract narrative text
2. Return empty state_changes
3. Log warning for monitoring
4. Game continues (no state update this turn)

## Cost Tracking

Add CloudWatch metrics for cost monitoring:

```python
# Log estimated cost per request
estimated_cost = (
    (usage.input_tokens * 0.25 / 1_000_000) +  # Input
    (usage.output_tokens * 1.25 / 1_000_000) +  # Output
    (getattr(usage, "cache_read_input_tokens", 0) * 0.025 / 1_000_000)  # Cached (90% off)
)
logger.info("Request cost", extra={"estimated_cost_usd": estimated_cost})
```

## Character Death Handling

If `character["hp"]` reaches 0 after applying state changes:

1. Set `session["status"] = "ended"`
2. Set `session["ended_reason"] = "character_death"`
3. Append final DM message describing death
4. Return response with `character_dead: true` flag
5. Future requests to this session return 400 "Session ended"

## Token Budget Verification

Before sending to Claude, verify total tokens are within budget:

| Component | Max Tokens |
|-----------|------------|
| System prompt | ~2000 |
| Character context | ~150 |
| World state | ~100 |
| Message history (10 msgs) | ~800 |
| Player action | ~100 |
| **Total input** | **~3150** |
| **Response** | **~500-800** |

If approaching limit, truncate message history first.

## Acceptance Criteria

- [ ] POST /sessions/{id}/action returns DM narrative
- [ ] State changes applied to character (HP, gold, XP, inventory)
- [ ] State changes applied to session (location, world_state)
- [ ] Message history updated with player action and DM response
- [ ] Prompt caching enabled and logged
- [ ] Claude API errors handled gracefully (429, 503, 500)
- [ ] Malformed JSON response falls back to narrative only
- [ ] Character death ends session
- [ ] Unit tests for service layer (>80% coverage)
- [ ] Integration test with mocked Claude client
- [ ] Manual test: send action, verify response in browser

## Testing Requirements

### Unit Tests
- `test_apply_state_changes_hp` - HP delta with bounds checking
- `test_apply_state_changes_inventory` - Add/remove items
- `test_apply_state_changes_location` - Location update
- `test_append_messages` - Message history growth
- `test_append_messages_trim` - Trims at 50 messages
- `test_character_death` - Session ends on 0 HP

### Integration Tests (mocked Claude)
- `test_full_action_flow` - End-to-end with mock client
- `test_api_error_handling` - Claude errors return proper HTTP status
- `test_malformed_response` - Falls back gracefully

### Manual Testing
1. Create character and session
2. Send action: "I look around"
3. Verify narrative response
4. Send action: "I attack the darkness" 
5. Verify dice rolls in response
6. Check DynamoDB for updated session/character

## Security Considerations

1. **API Key**: Never log or expose Claude API key
2. **Input Sanitization**: Trim and validate player action
3. **Rate Limiting**: Consider per-user rate limits (future)
4. **Cost Limits**: Monitor daily spend, alert on anomalies

## Out of Scope

- Combat initiation logic (init-09)
- Spell casting mechanics (future)
- Streaming responses (future optimization)
- Frontend UI (init-07)

## Notes

- First request per Lambda cold start creates new cache entry
- Cache TTL is 5 minutes (Anthropic default for ephemeral)
- Consider Lambda provisioned concurrency if cold starts are problematic
- Monitor cache hit rate in CloudWatch to validate cost savings
