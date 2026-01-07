# PRP-10: Cost Protection

**Created**: 2026-01-07
**Initial**: `initials/init-10-cost-protection.md`
**Status**: Implemented

---

## Overview

### Problem Statement

AWS Budget alerts have up to 6-hour delay before triggering actions, which is insufficient to prevent runaway AI costs in real-time. A single compromised session or abuse scenario could consume the entire monthly budget before AWS Budgets reacts.

With Mistral Small pricing ($1/$3 per 1M tokens) and a $20/month budget, real-time application-level cost controls are essential to:
1. Prevent global budget overruns
2. Limit individual session abuse
3. Provide graceful degradation with in-game messages
4. Enable monitoring and visibility into usage patterns

### Proposed Solution

Implement application-level token tracking using DynamoDB atomic counters with:
- **Global daily limit**: 500,000 tokens/day (~$1.10/day worst case)
- **Per-session daily limit**: 50,000 tokens/session/day
- **Pre-request limit checks** before calling Bedrock
- **Post-response usage recording** with atomic counters
- **In-game narrative messages** when limits are hit
- **CloudWatch metrics** for monitoring

### Success Criteria

- [ ] Global daily limit of 500K tokens enforced
- [ ] Per-session daily limit of 50K tokens enforced
- [ ] Limits checked BEFORE AI invocation (no wasted API calls)
- [ ] Usage recorded AFTER successful response
- [ ] In-game narrative messages displayed when limits hit
- [ ] DynamoDB items have TTL for auto-cleanup
- [ ] CloudWatch metrics track token consumption
- [ ] CloudWatch alarm triggers at 80% usage
- [ ] Frontend handles 429 responses gracefully
- [ ] All unit tests pass with >80% coverage
- [ ] Manual testing confirms limits work

---

## Context

### Related Documentation

- `docs/PLANNING.md` - Cost budget of $20/month
- `docs/DECISIONS.md` - ADR-009 (Mistral Small pricing: $1/$3 per 1M tokens)
- `initials/init-10-cost-protection.md` - Full specification

### Dependencies

- **Required**: PRP-09 Mistral DM migration (complete)
- **Required**: DynamoDB single-table design (exists)

### Files to Modify/Create

```
lambdas/shared/cost_limits.py      # NEW: Limit configuration
lambdas/shared/token_tracker.py    # NEW: DynamoDB tracking
lambdas/shared/cost_guard.py       # NEW: Limit checking
lambdas/dm/handler.py              # MODIFY: Add limit checks
lambdas/dm/service.py              # MODIFY: Return token usage
lambdas/dm/bedrock_client.py       # MODIFY: Return usage stats
lambdas/dm/models.py               # MODIFY: Add limit response model
cdk/stacks/api_stack.py            # MODIFY: Add CloudWatch alarms
frontend/src/types/index.ts        # MODIFY: Add limit types
frontend/src/services/sessions.ts  # MODIFY: Handle 429
lambdas/tests/test_cost_guard.py   # NEW: Unit tests
lambdas/tests/test_token_tracker.py # NEW: Unit tests
```

---

## Technical Specification

### Data Models

#### DynamoDB Items

```python
# Global daily usage counter
# PK: USAGE#GLOBAL
# SK: DATE#2026-01-07
{
    "PK": "USAGE#GLOBAL",
    "SK": "DATE#2026-01-07",
    "input_tokens": 125000,
    "output_tokens": 75000,
    "request_count": 500,
    "updated_at": "2026-01-07T15:30:00Z",
    "ttl": 1712345678  # 90 days from creation
}

# Per-session daily usage
# PK: SESSION#{session_id}
# SK: USAGE#DATE#2026-01-07
{
    "PK": "SESSION#abc-123",
    "SK": "USAGE#DATE#2026-01-07",
    "input_tokens": 25000,
    "output_tokens": 15000,
    "request_count": 100,
    "updated_at": "2026-01-07T15:30:00Z",
    "ttl": 1712000000  # 7 days from creation
}
```

#### Python Models

```python
# lambdas/shared/cost_limits.py
from dataclasses import dataclass

@dataclass(frozen=True)
class CostLimits:
    """Token limits for cost protection."""
    GLOBAL_DAILY_TOKENS: int = 500_000
    SESSION_DAILY_TOKENS: int = 50_000
    MAX_OUTPUT_TOKENS: int = 2_000
    WARNING_THRESHOLD: float = 0.8  # 80%


# lambdas/shared/cost_guard.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class LimitStatus:
    """Status of token limits."""
    allowed: bool
    reason: Optional[str] = None  # 'global_limit' | 'session_limit' | None
    global_usage: int = 0
    session_usage: int = 0
    global_remaining: int = 0
    session_remaining: int = 0


# lambdas/dm/models.py (add to existing)
class LimitReachedResponse(BaseModel):
    """Response when token limits are reached."""
    narrative: str
    limit_reached: bool = True
    reason: str  # 'global_limit' | 'session_limit'
```

#### TypeScript Types

```typescript
// frontend/src/types/index.ts (additions)

/** Response when token limits are reached */
export interface LimitReachedResponse {
  narrative: string;
  limit_reached: true;
  reason: 'global_limit' | 'session_limit';
}

/** Extended action response that may include limit info */
export type ActionResponseWithLimits = FullActionResponse | LimitReachedResponse;
```

### API Changes

| Method | Path | Status | Request | Response |
|--------|------|--------|---------|----------|
| POST | /sessions/{id}/action | 200 | `ActionRequest` | `FullActionResponse` |
| POST | /sessions/{id}/action | 429 | `ActionRequest` | `LimitReachedResponse` |

The 429 response includes an in-game narrative message so the frontend can display it naturally.

---

## Implementation Steps

### Step 1: Create Cost Limits Configuration

**Files**: `lambdas/shared/cost_limits.py`

Create a simple dataclass with limit constants.

```python
"""Cost protection limit configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CostLimits:
    """Token limits for cost protection.

    These limits prevent runaway costs from AI API calls.
    Limits reset at midnight UTC daily.
    """

    # Global daily limit (all users combined)
    # 500K tokens @ $1/$3 per 1M ≈ $1.10/day max
    GLOBAL_DAILY_TOKENS: int = 500_000

    # Per-session daily limit (single user session)
    # Prevents one user from consuming entire budget
    SESSION_DAILY_TOKENS: int = 50_000

    # Per-request output limit (sanity check)
    MAX_OUTPUT_TOKENS: int = 2_000

    # Warning threshold (log warning at this %)
    WARNING_THRESHOLD: float = 0.8
```

**Validation**:
- [ ] File created with correct constants
- [ ] Lint passes

### Step 2: Create Token Tracker Module

**Files**: `lambdas/shared/token_tracker.py`

Implement DynamoDB atomic counters for tracking usage.

```python
"""Token usage tracking for cost protection."""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import boto3
from aws_lambda_powertools import Logger

logger = Logger(child=True)


def get_today_key() -> str:
    """Get today's date key in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_ttl_epoch(days: int) -> int:
    """Get TTL epoch timestamp for auto-deletion."""
    future = datetime.now(timezone.utc) + timedelta(days=days)
    return int(future.timestamp())


class TokenTracker:
    """Tracks token usage in DynamoDB."""

    def __init__(self, table_name: str | None = None):
        """Initialize tracker with table name."""
        self.table_name = table_name or os.environ.get("TABLE_NAME", "")
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)

    def get_global_usage(self, date_key: str | None = None) -> dict:
        """Get global token usage for a date."""
        date_key = date_key or get_today_key()

        response = self.table.get_item(
            Key={"PK": "USAGE#GLOBAL", "SK": f"DATE#{date_key}"}
        )

        item = response.get("Item", {})
        return {
            "input_tokens": int(item.get("input_tokens", 0)),
            "output_tokens": int(item.get("output_tokens", 0)),
            "request_count": int(item.get("request_count", 0)),
        }

    def get_session_usage(
        self, session_id: str, date_key: str | None = None
    ) -> dict:
        """Get session token usage for a date."""
        date_key = date_key or get_today_key()

        response = self.table.get_item(
            Key={
                "PK": f"SESSION#{session_id}",
                "SK": f"USAGE#DATE#{date_key}",
            }
        )

        item = response.get("Item", {})
        return {
            "input_tokens": int(item.get("input_tokens", 0)),
            "output_tokens": int(item.get("output_tokens", 0)),
            "request_count": int(item.get("request_count", 0)),
        }

    def increment_usage(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[dict, dict]:
        """Increment both global and session usage atomically.

        Returns:
            Tuple of (global_usage, session_usage) after increment
        """
        date_key = get_today_key()
        now = datetime.now(timezone.utc).isoformat()

        # Update global counter
        global_response = self.table.update_item(
            Key={"PK": "USAGE#GLOBAL", "SK": f"DATE#{date_key}"},
            UpdateExpression="""
                SET input_tokens = if_not_exists(input_tokens, :zero) + :input,
                    output_tokens = if_not_exists(output_tokens, :zero) + :output,
                    request_count = if_not_exists(request_count, :zero) + :one,
                    updated_at = :now,
                    #ttl_attr = :ttl
            """,
            ExpressionAttributeNames={"#ttl_attr": "ttl"},
            ExpressionAttributeValues={
                ":input": Decimal(str(input_tokens)),
                ":output": Decimal(str(output_tokens)),
                ":zero": Decimal("0"),
                ":one": Decimal("1"),
                ":now": now,
                ":ttl": get_ttl_epoch(days=90),
            },
            ReturnValues="ALL_NEW",
        )

        # Update session counter
        session_response = self.table.update_item(
            Key={
                "PK": f"SESSION#{session_id}",
                "SK": f"USAGE#DATE#{date_key}",
            },
            UpdateExpression="""
                SET input_tokens = if_not_exists(input_tokens, :zero) + :input,
                    output_tokens = if_not_exists(output_tokens, :zero) + :output,
                    request_count = if_not_exists(request_count, :zero) + :one,
                    updated_at = :now,
                    #ttl_attr = :ttl
            """,
            ExpressionAttributeNames={"#ttl_attr": "ttl"},
            ExpressionAttributeValues={
                ":input": Decimal(str(input_tokens)),
                ":output": Decimal(str(output_tokens)),
                ":zero": Decimal("0"),
                ":one": Decimal("1"),
                ":now": now,
                ":ttl": get_ttl_epoch(days=7),
            },
            ReturnValues="ALL_NEW",
        )

        global_item = global_response["Attributes"]
        session_item = session_response["Attributes"]

        logger.info(
            "Token usage recorded",
            extra={
                "session_id": session_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "global_total": int(global_item["input_tokens"])
                    + int(global_item["output_tokens"]),
                "session_total": int(session_item["input_tokens"])
                    + int(session_item["output_tokens"]),
            },
        )

        return (
            {
                "input_tokens": int(global_item["input_tokens"]),
                "output_tokens": int(global_item["output_tokens"]),
                "request_count": int(global_item["request_count"]),
            },
            {
                "input_tokens": int(session_item["input_tokens"]),
                "output_tokens": int(session_item["output_tokens"]),
                "request_count": int(session_item["request_count"]),
            },
        )
```

**Validation**:
- [ ] File created
- [ ] Lint passes
- [ ] Unit tests pass

### Step 3: Create Cost Guard Module

**Files**: `lambdas/shared/cost_guard.py`

Implement limit checking and in-game message generation.

```python
"""Cost protection guard for AI requests."""

from dataclasses import dataclass
from typing import Optional

from aws_lambda_powertools import Logger

from .cost_limits import CostLimits
from .token_tracker import TokenTracker

logger = Logger(child=True)


@dataclass
class LimitStatus:
    """Status of token limits."""

    allowed: bool
    reason: Optional[str] = None
    global_usage: int = 0
    session_usage: int = 0
    global_remaining: int = 0
    session_remaining: int = 0


class CostGuard:
    """Guards against exceeding token limits."""

    def __init__(self, tracker: TokenTracker | None = None):
        """Initialize guard with optional tracker."""
        self.tracker = tracker or TokenTracker()
        self.limits = CostLimits()

    def check_limits(self, session_id: str) -> LimitStatus:
        """Check if request is allowed under current limits.

        Args:
            session_id: Current session ID

        Returns:
            LimitStatus indicating if request should proceed
        """
        global_usage = self.tracker.get_global_usage()
        session_usage = self.tracker.get_session_usage(session_id)

        global_total = global_usage["input_tokens"] + global_usage["output_tokens"]
        session_total = session_usage["input_tokens"] + session_usage["output_tokens"]

        global_remaining = self.limits.GLOBAL_DAILY_TOKENS - global_total
        session_remaining = self.limits.SESSION_DAILY_TOKENS - session_total

        # Check global limit
        if global_total >= self.limits.GLOBAL_DAILY_TOKENS:
            logger.warning(
                "Global daily limit reached",
                extra={
                    "global_tokens": global_total,
                    "limit": self.limits.GLOBAL_DAILY_TOKENS,
                },
            )
            return LimitStatus(
                allowed=False,
                reason="global_limit",
                global_usage=global_total,
                session_usage=session_total,
                global_remaining=0,
                session_remaining=session_remaining,
            )

        # Check session limit
        if session_total >= self.limits.SESSION_DAILY_TOKENS:
            logger.warning(
                "Session daily limit reached",
                extra={
                    "session_id": session_id,
                    "session_tokens": session_total,
                    "limit": self.limits.SESSION_DAILY_TOKENS,
                },
            )
            return LimitStatus(
                allowed=False,
                reason="session_limit",
                global_usage=global_total,
                session_usage=session_total,
                global_remaining=global_remaining,
                session_remaining=0,
            )

        # Log warning if approaching limits
        if global_total >= self.limits.GLOBAL_DAILY_TOKENS * self.limits.WARNING_THRESHOLD:
            logger.warning(
                "Approaching global daily limit",
                extra={
                    "global_tokens": global_total,
                    "limit": self.limits.GLOBAL_DAILY_TOKENS,
                    "percentage": round(global_total / self.limits.GLOBAL_DAILY_TOKENS * 100, 1),
                },
            )

        return LimitStatus(
            allowed=True,
            global_usage=global_total,
            session_usage=session_total,
            global_remaining=global_remaining,
            session_remaining=session_remaining,
        )


def get_limit_message(reason: str) -> str:
    """Get in-game narrative message for limit hit.

    Returns a message that fits the game world.
    """
    if reason == "global_limit":
        return (
            "**The dungeon grows silent...**\n\n"
            "*A strange exhaustion settles over the realm. "
            "The spirits that guide your adventure have grown weary "
            "and must rest until the morrow.*\n\n"
            "The Chaos Dungeon will awaken again at midnight UTC. "
            "Your progress has been saved."
        )

    if reason == "session_limit":
        return (
            "**You feel a strange fatigue...**\n\n"
            "*The magical energies that power your journey have been "
            "depleted for today. Rest now, brave adventurer.*\n\n"
            "Your session limit has been reached. "
            "Return tomorrow for more adventures, or start a new session."
        )

    return "The dungeon is temporarily unavailable. Please try again later."
```

**Validation**:
- [ ] File created
- [ ] Lint passes
- [ ] Unit tests pass

### Step 4: Update Bedrock Client to Return Usage

**Files**: `lambdas/dm/bedrock_client.py`

Modify `invoke_mistral` to return a dict with text and usage stats instead of just text.

```python
# Add new return type
from dataclasses import dataclass

@dataclass
class MistralResponse:
    """Response from Mistral invocation."""
    text: str
    input_tokens: int
    output_tokens: int


# Update invoke_mistral to return MistralResponse
def invoke_mistral(
    self,
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.8,
    top_p: float = 0.95,
) -> MistralResponse:
    """Invoke Mistral Small via Bedrock.

    Returns:
        MistralResponse with text and estimated token counts
    """
    # ... existing code ...

    result = json.loads(response["body"].read())
    output_text = result["outputs"][0]["text"]

    # Estimate tokens (Mistral doesn't return counts)
    input_tokens = int(len(prompt.split()) * 1.3)
    output_tokens = int(len(output_text.split()) * 1.3)

    # ... existing logging ...

    return MistralResponse(
        text=output_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
```

Also update `send_action` to return `MistralResponse`.

**Validation**:
- [ ] Method updated
- [ ] Lint passes
- [ ] Existing tests updated

### Step 5: Integrate Cost Protection into DM Handler

**Files**: `lambdas/dm/handler.py`

Add limit checking before processing and usage recording after.

```python
# Add imports
from shared.cost_guard import CostGuard, get_limit_message
from shared.token_tracker import TokenTracker

# Add to handler
_cost_guard: CostGuard | None = None

def get_cost_guard() -> CostGuard:
    """Get or create the cost guard singleton."""
    global _cost_guard
    if _cost_guard is None:
        tracker = TokenTracker(config.table_name)
        _cost_guard = CostGuard(tracker)
    return _cost_guard


@app.post("/sessions/<session_id>/action")
@tracer.capture_method
def post_action(session_id: str) -> Response:
    """Process a player action."""
    user_id = get_user_id()

    # ... validation code ...

    # Check limits BEFORE calling AI
    cost_guard = get_cost_guard()
    limit_status = cost_guard.check_limits(session_id)

    if not limit_status.allowed:
        return Response(
            status_code=429,
            content_type="application/json",
            body=json.dumps({
                "narrative": get_limit_message(limit_status.reason),
                "limit_reached": True,
                "reason": limit_status.reason,
            }),
        )

    # Process action (existing code)
    service = get_service()
    response = service.process_action(...)

    # Record usage AFTER successful response
    # (usage recording happens in service layer)

    return Response(...)
```

**Validation**:
- [ ] Limit check added before AI call
- [ ] 429 response returns in-game message
- [ ] Lint passes

### Step 6: Update DM Service to Record Usage

**Files**: `lambdas/dm/service.py`

Add token recording after successful AI responses.

```python
# Add imports
from shared.token_tracker import TokenTracker

# Add to __init__
self.token_tracker = TokenTracker()

# In _process_normal_action and _process_combat_action, after AI call:
response = client.send_action(system_prompt, context, action)

# Record usage
self.token_tracker.increment_usage(
    session_id=session_id,
    input_tokens=response.input_tokens,
    output_tokens=response.output_tokens,
)
```

**Validation**:
- [ ] Usage recording added
- [ ] Lint passes
- [ ] Tests updated

### Step 7: Add CloudWatch Metrics

**Files**: `lambdas/dm/handler.py`

Add Powertools Metrics for monitoring.

```python
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

metrics = Metrics(namespace="ChaosDungeon")

@app.post("/sessions/<session_id>/action")
@tracer.capture_method
def post_action(session_id: str) -> Response:
    # ... existing code ...

    # After limit check fails
    if not limit_status.allowed:
        metrics.add_metric(
            name="LimitHits",
            unit=MetricUnit.Count,
            value=1,
        )
        metrics.add_dimension(name="Reason", value=limit_status.reason)
        return Response(status_code=429, ...)

    # After successful processing
    metrics.add_metric(
        name="TokensConsumed",
        unit=MetricUnit.Count,
        value=response.input_tokens + response.output_tokens,
    )

    return Response(...)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics  # Add this decorator
def lambda_handler(event, context):
    return app.resolve(event, context)
```

**Validation**:
- [ ] Metrics added
- [ ] Lint passes

### Step 8: Add CloudWatch Alarms (CDK)

**Files**: `cdk/stacks/api_stack.py`

Add alarms for high usage and limit hits.

```python
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions

# In _create_dm_lambda or new method:

# High usage alarm (80% of daily limit)
high_usage_alarm = cloudwatch.Alarm(
    self,
    "HighTokenUsageAlarm",
    metric=cloudwatch.Metric(
        namespace="ChaosDungeon",
        metric_name="TokensConsumed",
        statistic="Sum",
        period=Duration.hours(24),
    ),
    threshold=400_000,  # 80% of 500K
    evaluation_periods=1,
    alarm_description="Daily token usage approaching limit (80%)",
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
)

# Limit hit alarm
limit_hit_alarm = cloudwatch.Alarm(
    self,
    "LimitHitAlarm",
    metric=cloudwatch.Metric(
        namespace="ChaosDungeon",
        metric_name="LimitHits",
        statistic="Sum",
        period=Duration.hours(1),
    ),
    threshold=1,
    evaluation_periods=1,
    alarm_description="Token limit was hit",
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
)
```

Note: SNS topic for email alerts is optional and can be added later.

**Validation**:
- [ ] Alarms defined in CDK
- [ ] `cdk synth` passes

### Step 9: Update Frontend to Handle 429

**Files**: `frontend/src/types/index.ts`, `frontend/src/services/sessions.ts`

Add types and handle limit responses.

```typescript
// frontend/src/types/index.ts - add:
export interface LimitReachedResponse {
  narrative: string;
  limit_reached: true;
  reason: 'global_limit' | 'session_limit';
}

export function isLimitReached(
  response: FullActionResponse | LimitReachedResponse
): response is LimitReachedResponse {
  return 'limit_reached' in response && response.limit_reached === true;
}
```

```typescript
// frontend/src/services/sessions.ts - update sendAction:
sendAction: async (sessionId: string, action: string) => {
  const response = await fetch(`${API_URL}/sessions/${sessionId}/action`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ action }),
  });

  // Handle 429 as a valid response (has narrative)
  if (response.status === 429) {
    const data = await response.json();
    return data as LimitReachedResponse;
  }

  if (!response.ok) {
    throw new ApiRequestError(response.status, 'Failed to send action');
  }

  return response.json() as Promise<FullActionResponse>;
},
```

**Validation**:
- [ ] Types added
- [ ] Service handles 429
- [ ] Frontend tests pass

### Step 10: Write Unit Tests

**Files**: `lambdas/tests/test_cost_guard.py`, `lambdas/tests/test_token_tracker.py`

```python
# test_cost_guard.py
import pytest
from unittest.mock import MagicMock, patch

from shared.cost_guard import CostGuard, LimitStatus, get_limit_message
from shared.cost_limits import CostLimits


class TestCostGuard:
    """Tests for CostGuard."""

    def test_allows_request_under_limit(self):
        """Request allowed when under all limits."""
        mock_tracker = MagicMock()
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 1000, "output_tokens": 500, "request_count": 5
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 100, "output_tokens": 50, "request_count": 1
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is True
        assert status.reason is None

    def test_blocks_at_global_limit(self):
        """Request blocked when global limit reached."""
        mock_tracker = MagicMock()
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 300000, "output_tokens": 200000, "request_count": 1000
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 100, "output_tokens": 50, "request_count": 1
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is False
        assert status.reason == "global_limit"

    def test_blocks_at_session_limit(self):
        """Request blocked when session limit reached."""
        mock_tracker = MagicMock()
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 1000, "output_tokens": 500, "request_count": 5
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 30000, "output_tokens": 20000, "request_count": 100
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is False
        assert status.reason == "session_limit"


class TestGetLimitMessage:
    """Tests for get_limit_message."""

    def test_global_limit_message(self):
        """Global limit message is narrative."""
        msg = get_limit_message("global_limit")
        assert "dungeon grows silent" in msg.lower()
        assert "midnight UTC" in msg

    def test_session_limit_message(self):
        """Session limit message is narrative."""
        msg = get_limit_message("session_limit")
        assert "fatigue" in msg.lower()
        assert "session limit" in msg.lower()
```

**Validation**:
- [ ] Tests created
- [ ] All tests pass
- [ ] Coverage > 80%

---

## Testing Requirements

### Unit Tests

| Test | Description |
|------|-------------|
| `test_allows_under_limit` | Requests allowed when usage below limits |
| `test_blocks_at_global_limit` | 429 when global 500K limit reached |
| `test_blocks_at_session_limit` | 429 when session 50K limit reached |
| `test_increment_usage` | Atomic counters update correctly |
| `test_warning_logged_at_80pct` | Warning logged at 80% threshold |
| `test_limit_message_content` | In-game messages are appropriate |
| `test_ttl_set_correctly` | TTL values set for auto-cleanup |

### Integration Tests

1. Deploy to dev environment
2. Make requests until session limit (~50 requests)
3. Verify 429 response with narrative message
4. Verify new session can still make requests
5. Check DynamoDB items have correct values
6. Verify CloudWatch metrics appear

### Manual Testing

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start session, send ~50 actions rapidly | Session limit message appears |
| 2 | Start new session | New session works normally |
| 3 | Check DynamoDB | Usage items exist with TTL |
| 4 | Check CloudWatch | TokensConsumed metric visible |
| 5 | Verify message text | Narrative fits game world |

---

## Integration Test Plan

### Prerequisites

- Backend deployed: `cd cdk && cdk deploy --all`
- Frontend running: `cd frontend && npm run dev`
- Browser DevTools open (Console + Network tabs)

### Test Steps

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Send 5 actions normally | 200 responses with narrative | ☐ |
| 2 | Check CloudWatch console | TokensConsumed metric exists | ☐ |
| 3 | Check DynamoDB | USAGE#GLOBAL item exists | ☐ |
| 4 | Simulate limit (lower limit for test) | 429 with in-game message | ☐ |
| 5 | Message displays in chat UI | Narrative shows naturally | ☐ |
| 6 | New session after limit | New session works | ☐ |

### Error Scenarios

| Scenario | How to Trigger | Expected Behavior |
|----------|----------------|-------------------|
| Global limit hit | Exhaust 500K tokens | 429 + global message |
| Session limit hit | Exhaust 50K tokens in session | 429 + session message |
| DynamoDB error | (Hard to test) | 500 error, graceful degradation |

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| Global limit reached | 500K tokens/day consumed | 429 + in-game message |
| Session limit reached | 50K tokens/session/day | 429 + in-game message |
| DynamoDB error | AWS issues | Log error, continue without tracking |

### Edge Cases

- **Midnight rollover**: Usage resets automatically via date key
- **DynamoDB race conditions**: Atomic updates prevent issues
- **Missing usage item**: Starts at 0, created on first increment
- **TTL cleanup**: Items auto-deleted after 7/90 days

---

## Cost Impact

### Claude/Mistral API

- No change to per-token costs
- Prevents cost overruns via limits
- Maximum daily spend capped at ~$1.10

### AWS

| Resource | Cost | Notes |
|----------|------|-------|
| DynamoDB writes | ~$0.01/day | Atomic counter updates |
| DynamoDB reads | ~$0.01/day | Limit checks |
| CloudWatch metrics | ~$0.30/month | Custom metrics |
| CloudWatch alarms | ~$0.20/month | 2 alarms |
| **Total new cost** | ~$0.52/month | Minimal overhead |

---

## Open Questions

1. ~~Should we expose remaining tokens to frontend?~~ — No, keep it simple for MVP
2. ~~Should limits be configurable via SSM Parameter Store?~~ — No, hardcode for now
3. Consider adding per-user limits when authentication is added (future)

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Well-defined scope from detailed init spec |
| Feasibility | 9 | Uses existing patterns (DynamoDB, Powertools) |
| Completeness | 9 | Covers all aspects including tests |
| Alignment | 10 | Directly addresses budget protection |
| **Overall** | **9.25** | High confidence |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
