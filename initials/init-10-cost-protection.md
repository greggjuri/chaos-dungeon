# init-10-cost-protection

## Overview

Implement application-level token tracking and daily limits to prevent runaway AI costs. This provides real-time cost protection that AWS Budget alerts cannot offer (Budget alerts have up to 6-hour delay).

## Dependencies

- init-09-mistral-dm (Mistral integration complete)
- DynamoDB table exists with single-table design

## Goals

1. **Daily global limit** — 500,000 tokens/day hard cap (~$1.10/day max)
2. **Per-session limits** — Prevent single user from consuming entire budget
3. **Graceful degradation** — Return friendly in-game message when limits hit
4. **Visibility** — Track usage for monitoring and adjustments
5. **Zero additional cost** — Use existing DynamoDB table

## Background

### Cost Calculation (Mistral Small)

| Token Type | Price per 1K | 
|------------|--------------|
| Input      | $0.001       |
| Output     | $0.003       |

Assuming 40% input / 60% output mix:
- 500K tokens/day ≈ $1.10/day
- Monthly max (if limit hit daily) ≈ $33/month

This provides buffer above the $20/month target while preventing catastrophic overruns.

### Why Application-Level?

- **AWS Budgets**: Updates only 4x/day, up to 6-hour delay before action triggers
- **API Gateway throttling**: Limits requests, not token consumption
- **Application-level**: Real-time, per-request enforcement

## Data Model

### DynamoDB Items

Add two new item types to existing single-table design:

```
# Global daily usage counter
PK: USAGE#GLOBAL
SK: DATE#2025-01-07
Attributes:
  - input_tokens: number
  - output_tokens: number
  - request_count: number
  - updated_at: ISO timestamp
  - ttl: epoch timestamp (auto-delete after 90 days)

# Per-session daily usage
PK: SESSION#{session_id}  
SK: USAGE#DATE#2025-01-07
Attributes:
  - input_tokens: number
  - output_tokens: number
  - request_count: number
  - updated_at: ISO timestamp
  - ttl: epoch timestamp (auto-delete after 7 days)
```

### Limits Configuration

```python
# lambdas/shared/cost_limits.py

from dataclasses import dataclass

@dataclass(frozen=True)
class CostLimits:
    """Token limits for cost protection."""
    
    # Global daily limit (all users combined)
    GLOBAL_DAILY_TOKENS: int = 500_000
    
    # Per-session daily limit (single user)
    SESSION_DAILY_TOKENS: int = 50_000
    
    # Per-request sanity limit
    MAX_OUTPUT_TOKENS: int = 2_000
    
    # Warning thresholds (percentage of limit)
    WARNING_THRESHOLD: float = 0.8  # 80%
```

## Implementation Steps

### Step 1: Create Token Tracker Module

Create `lambdas/shared/token_tracker.py`:

```python
"""Track token usage for cost protection."""

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
import boto3
from aws_lambda_powertools import Logger

logger = Logger()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])


def get_today_key() -> str:
    """Get today's date key in UTC."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def get_ttl_epoch(days: int = 90) -> int:
    """Get TTL epoch timestamp for auto-deletion."""
    from datetime import timedelta
    future = datetime.now(timezone.utc) + timedelta(days=days)
    return int(future.timestamp())


def get_global_usage(date_key: Optional[str] = None) -> dict:
    """Get global token usage for a date.
    
    Returns:
        Dict with input_tokens, output_tokens, request_count
    """
    date_key = date_key or get_today_key()
    
    response = table.get_item(
        Key={
            'PK': 'USAGE#GLOBAL',
            'SK': f'DATE#{date_key}'
        }
    )
    
    item = response.get('Item', {})
    return {
        'input_tokens': int(item.get('input_tokens', 0)),
        'output_tokens': int(item.get('output_tokens', 0)),
        'request_count': int(item.get('request_count', 0)),
    }


def get_session_usage(session_id: str, date_key: Optional[str] = None) -> dict:
    """Get session token usage for a date."""
    date_key = date_key or get_today_key()
    
    response = table.get_item(
        Key={
            'PK': f'SESSION#{session_id}',
            'SK': f'USAGE#DATE#{date_key}'
        }
    )
    
    item = response.get('Item', {})
    return {
        'input_tokens': int(item.get('input_tokens', 0)),
        'output_tokens': int(item.get('output_tokens', 0)),
        'request_count': int(item.get('request_count', 0)),
    }


def increment_usage(
    session_id: str,
    input_tokens: int,
    output_tokens: int
) -> Tuple[dict, dict]:
    """Increment both global and session usage atomically.
    
    Args:
        session_id: Current session ID
        input_tokens: Input tokens consumed
        output_tokens: Output tokens consumed
        
    Returns:
        Tuple of (global_usage, session_usage) after increment
    """
    date_key = get_today_key()
    now = datetime.now(timezone.utc).isoformat()
    
    # Update global counter
    global_response = table.update_item(
        Key={
            'PK': 'USAGE#GLOBAL',
            'SK': f'DATE#{date_key}'
        },
        UpdateExpression='''
            SET input_tokens = if_not_exists(input_tokens, :zero) + :input,
                output_tokens = if_not_exists(output_tokens, :zero) + :output,
                request_count = if_not_exists(request_count, :zero) + :one,
                updated_at = :now,
                #ttl = :ttl
        ''',
        ExpressionAttributeNames={'#ttl': 'ttl'},
        ExpressionAttributeValues={
            ':input': Decimal(str(input_tokens)),
            ':output': Decimal(str(output_tokens)),
            ':zero': Decimal('0'),
            ':one': Decimal('1'),
            ':now': now,
            ':ttl': get_ttl_epoch(days=90),
        },
        ReturnValues='ALL_NEW'
    )
    
    # Update session counter
    session_response = table.update_item(
        Key={
            'PK': f'SESSION#{session_id}',
            'SK': f'USAGE#DATE#{date_key}'
        },
        UpdateExpression='''
            SET input_tokens = if_not_exists(input_tokens, :zero) + :input,
                output_tokens = if_not_exists(output_tokens, :zero) + :output,
                request_count = if_not_exists(request_count, :zero) + :one,
                updated_at = :now,
                #ttl = :ttl
        ''',
        ExpressionAttributeNames={'#ttl': 'ttl'},
        ExpressionAttributeValues={
            ':input': Decimal(str(input_tokens)),
            ':output': Decimal(str(output_tokens)),
            ':zero': Decimal('0'),
            ':one': Decimal('1'),
            ':now': now,
            ':ttl': get_ttl_epoch(days=7),
        },
        ReturnValues='ALL_NEW'
    )
    
    global_item = global_response['Attributes']
    session_item = session_response['Attributes']
    
    return (
        {
            'input_tokens': int(global_item['input_tokens']),
            'output_tokens': int(global_item['output_tokens']),
            'request_count': int(global_item['request_count']),
        },
        {
            'input_tokens': int(session_item['input_tokens']),
            'output_tokens': int(session_item['output_tokens']),
            'request_count': int(session_item['request_count']),
        }
    )
```

### Step 2: Create Limit Checker

Create `lambdas/shared/cost_guard.py`:

```python
"""Cost protection guard for AI requests."""

from dataclasses import dataclass
from typing import Optional, Tuple
from aws_lambda_powertools import Logger

from .cost_limits import CostLimits
from .token_tracker import get_global_usage, get_session_usage

logger = Logger()


@dataclass
class LimitStatus:
    """Status of token limits."""
    allowed: bool
    reason: Optional[str] = None
    global_usage: int = 0
    session_usage: int = 0
    global_remaining: int = 0
    session_remaining: int = 0


def check_limits(session_id: str) -> LimitStatus:
    """Check if request is allowed under current limits.
    
    Args:
        session_id: Current session ID
        
    Returns:
        LimitStatus indicating if request should proceed
    """
    limits = CostLimits()
    
    global_usage = get_global_usage()
    session_usage = get_session_usage(session_id)
    
    global_total = global_usage['input_tokens'] + global_usage['output_tokens']
    session_total = session_usage['input_tokens'] + session_usage['output_tokens']
    
    global_remaining = limits.GLOBAL_DAILY_TOKENS - global_total
    session_remaining = limits.SESSION_DAILY_TOKENS - session_total
    
    # Check global limit
    if global_total >= limits.GLOBAL_DAILY_TOKENS:
        logger.warning(
            "Global daily limit reached",
            extra={
                'global_tokens': global_total,
                'limit': limits.GLOBAL_DAILY_TOKENS
            }
        )
        return LimitStatus(
            allowed=False,
            reason='global_limit',
            global_usage=global_total,
            session_usage=session_total,
            global_remaining=0,
            session_remaining=session_remaining,
        )
    
    # Check session limit
    if session_total >= limits.SESSION_DAILY_TOKENS:
        logger.warning(
            "Session daily limit reached",
            extra={
                'session_id': session_id,
                'session_tokens': session_total,
                'limit': limits.SESSION_DAILY_TOKENS
            }
        )
        return LimitStatus(
            allowed=False,
            reason='session_limit',
            global_usage=global_total,
            session_usage=session_total,
            global_remaining=global_remaining,
            session_remaining=0,
        )
    
    # Log warning if approaching limits
    if global_total >= limits.GLOBAL_DAILY_TOKENS * limits.WARNING_THRESHOLD:
        logger.warning(
            "Approaching global daily limit",
            extra={
                'global_tokens': global_total,
                'limit': limits.GLOBAL_DAILY_TOKENS,
                'percentage': global_total / limits.GLOBAL_DAILY_TOKENS * 100
            }
        )
    
    return LimitStatus(
        allowed=True,
        global_usage=global_total,
        session_usage=session_total,
        global_remaining=global_remaining,
        session_remaining=session_remaining,
    )


def get_limit_message(reason: str) -> str:
    """Get in-game message for limit hit.
    
    Returns a narrative message that fits the game world.
    """
    if reason == 'global_limit':
        return (
            "**The dungeon grows silent...**\n\n"
            "*A strange exhaustion settles over the realm. "
            "The spirits that guide your adventure have grown weary "
            "and must rest until the morrow.*\n\n"
            "The Chaos Dungeon will awaken again at midnight UTC. "
            "Your progress has been saved."
        )
    
    if reason == 'session_limit':
        return (
            "**You feel a strange fatigue...**\n\n"
            "*The magical energies that power your journey have been "
            "depleted for today. Rest now, brave adventurer.*\n\n"
            "Your session limit has been reached. "
            "Return tomorrow for more adventures, or start a new session."
        )
    
    return "The dungeon is temporarily unavailable. Please try again later."
```

### Step 3: Integrate with Action Handler

Modify `lambdas/dm/handler.py` (or equivalent action handler):

```python
from shared.cost_guard import check_limits, get_limit_message, LimitStatus
from shared.token_tracker import increment_usage

def handle_action(event: dict, context) -> dict:
    """Handle player action with cost protection."""
    
    session_id = event['session_id']
    action = event['action']
    
    # Check limits BEFORE calling AI
    limit_status = check_limits(session_id)
    
    if not limit_status.allowed:
        return {
            'statusCode': 429,
            'body': {
                'narrative': get_limit_message(limit_status.reason),
                'limit_reached': True,
                'reason': limit_status.reason,
            }
        }
    
    # Call Mistral via Bedrock
    response = invoke_mistral(prompt)
    
    # Extract token counts from Bedrock response
    # Bedrock returns usage in response metadata
    input_tokens = response.get('usage', {}).get('input_tokens', 0)
    output_tokens = response.get('usage', {}).get('output_tokens', 0)
    
    # If Bedrock doesn't return usage, estimate
    if input_tokens == 0:
        input_tokens = estimate_tokens(prompt)
    if output_tokens == 0:
        output_tokens = estimate_tokens(response['text'])
    
    # Record usage AFTER successful response
    global_usage, session_usage = increment_usage(
        session_id=session_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )
    
    # Log for monitoring
    logger.info(
        "Token usage recorded",
        extra={
            'session_id': session_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'global_total': global_usage['input_tokens'] + global_usage['output_tokens'],
            'session_total': session_usage['input_tokens'] + session_usage['output_tokens'],
        }
    )
    
    return {
        'statusCode': 200,
        'body': {
            'narrative': response['text'],
            # ... other response fields
        }
    }


def estimate_tokens(text: str) -> int:
    """Rough token estimate when not provided by API.
    
    Mistral uses ~1.3 tokens per word on average.
    """
    words = len(text.split())
    return int(words * 1.3)
```

### Step 4: Update Bedrock Client to Return Usage

Modify `lambdas/shared/bedrock_client.py`:

```python
def invoke_mistral(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.8,
) -> dict:
    """Invoke Mistral and return response with usage stats.
    
    Returns:
        Dict with 'text' and 'usage' keys
    """
    body = json.dumps({
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
    })
    
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    
    result = json.loads(response['body'].read())
    
    return {
        'text': result['outputs'][0]['text'],
        'usage': {
            # Bedrock Mistral may not return token counts
            # Check response structure and extract if available
            'input_tokens': result.get('usage', {}).get('prompt_tokens', 0),
            'output_tokens': result.get('usage', {}).get('completion_tokens', 0),
        }
    }
```

### Step 5: Add CloudWatch Metrics

Add metrics for monitoring in `lambdas/dm/handler.py`:

```python
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

metrics = Metrics(namespace="ChaosDungeon")

@metrics.log_metrics
def handle_action(event: dict, context) -> dict:
    # ... existing code ...
    
    # Add metrics after recording usage
    metrics.add_metric(
        name="TokensConsumed",
        unit=MetricUnit.Count,
        value=input_tokens + output_tokens
    )
    
    metrics.add_metric(
        name="InputTokens",
        unit=MetricUnit.Count,
        value=input_tokens
    )
    
    metrics.add_metric(
        name="OutputTokens",
        unit=MetricUnit.Count,
        value=output_tokens
    )
    
    # Track limit status
    if not limit_status.allowed:
        metrics.add_metric(
            name="LimitHits",
            unit=MetricUnit.Count,
            value=1
        )
```

### Step 6: Create CloudWatch Alarms (CDK)

Add to CDK stack:

```python
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_sns as sns

# Create SNS topic for alerts
alerts_topic = sns.Topic(self, "CostAlerts")
alerts_topic.add_subscription(
    sns_subscriptions.EmailSubscription("your-email@example.com")
)

# Alarm when daily tokens exceed 80% of limit (400K)
high_usage_alarm = cloudwatch.Alarm(
    self, "HighTokenUsageAlarm",
    metric=cloudwatch.Metric(
        namespace="ChaosDungeon",
        metric_name="TokensConsumed",
        statistic="Sum",
        period=Duration.hours(24),
    ),
    threshold=400_000,  # 80% of 500K
    evaluation_periods=1,
    alarm_description="Daily token usage approaching limit",
)
high_usage_alarm.add_alarm_action(cw_actions.SnsAction(alerts_topic))

# Alarm when limit is hit
limit_hit_alarm = cloudwatch.Alarm(
    self, "LimitHitAlarm",
    metric=cloudwatch.Metric(
        namespace="ChaosDungeon",
        metric_name="LimitHits",
        statistic="Sum",
        period=Duration.hours(1),
    ),
    threshold=1,
    evaluation_periods=1,
    alarm_description="Token limit was hit",
)
limit_hit_alarm.add_alarm_action(cw_actions.SnsAction(alerts_topic))
```

## Frontend Integration

### Handle 429 Response

Update frontend to handle limit responses gracefully:

```typescript
// frontend/src/api/game.ts

interface ActionResponse {
  narrative: string;
  limit_reached?: boolean;
  reason?: 'global_limit' | 'session_limit';
  // ... other fields
}

async function sendAction(action: string): Promise<ActionResponse> {
  const response = await fetch('/api/action', {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
  
  const data = await response.json();
  
  // Handle limit reached - still show narrative (the in-game message)
  if (response.status === 429 || data.limit_reached) {
    return {
      ...data,
      // Optionally show a toast/banner
      _limitReached: true,
    };
  }
  
  return data;
}
```

## Testing Plan

### Unit Tests

```python
# lambdas/tests/test_cost_guard.py

def test_allows_request_under_limit():
    """Request allowed when under all limits."""
    # Mock get_global_usage to return low values
    status = check_limits("test-session")
    assert status.allowed is True

def test_blocks_at_global_limit():
    """Request blocked when global limit reached."""
    # Mock get_global_usage to return 500K tokens
    status = check_limits("test-session")
    assert status.allowed is False
    assert status.reason == 'global_limit'

def test_blocks_at_session_limit():
    """Request blocked when session limit reached."""
    # Mock get_session_usage to return 50K tokens
    status = check_limits("test-session")
    assert status.allowed is False
    assert status.reason == 'session_limit'

def test_increment_updates_both_counters():
    """Increment updates global and session atomically."""
    global_usage, session_usage = increment_usage(
        session_id="test",
        input_tokens=100,
        output_tokens=200
    )
    assert global_usage['input_tokens'] >= 100
    assert session_usage['output_tokens'] >= 200
```

### Integration Tests

1. Deploy to dev environment
2. Make requests until session limit (50K tokens)
3. Verify 429 response with narrative message
4. Verify new session can still make requests
5. Check DynamoDB items have correct values
6. Verify CloudWatch metrics appear

### Manual Tests

1. **Session limit test**: Rapidly make ~50 requests, verify limit message appears
2. **Cross-session test**: After hitting session limit, new session works
3. **Midnight rollover**: Verify counters reset at UTC midnight (check TTL behavior)
4. **Message quality**: Verify limit messages fit game narrative

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `lambdas/shared/cost_limits.py` | CREATE | Limit configuration dataclass |
| `lambdas/shared/token_tracker.py` | CREATE | DynamoDB token tracking |
| `lambdas/shared/cost_guard.py` | CREATE | Limit checking and messages |
| `lambdas/dm/handler.py` | MODIFY | Add limit checks and usage recording |
| `lambdas/shared/bedrock_client.py` | MODIFY | Return usage stats |
| `cdk/stacks/api_stack.py` | MODIFY | Add CloudWatch alarms |
| `frontend/src/api/game.ts` | MODIFY | Handle 429 responses |
| `lambdas/tests/test_cost_guard.py` | CREATE | Unit tests |
| `lambdas/tests/test_token_tracker.py` | CREATE | Unit tests |

## Acceptance Criteria

- [ ] Global daily limit of 500K tokens enforced
- [ ] Per-session daily limit of 50K tokens enforced
- [ ] Limits checked BEFORE AI invocation (no wasted calls)
- [ ] Usage recorded AFTER successful response
- [ ] In-game narrative messages for limit hits
- [ ] DynamoDB items have TTL for auto-cleanup
- [ ] CloudWatch metrics track token consumption
- [ ] CloudWatch alarm at 80% usage
- [ ] Frontend handles 429 gracefully
- [ ] Unit tests pass with >80% coverage
- [ ] Manual testing confirms limits work

## Out of Scope

- AWS Budget Actions (future enhancement)
- Per-user limits (requires auth, not in anonymous sessions)
- Real-time cost calculation (tokens only, not dollars)
- Admin dashboard for usage (use CloudWatch)
- Adjustable limits via API (hardcoded for now)

## Notes

- Token counts from Bedrock may not be exact; estimation fallback included
- TTL on usage items prevents unbounded DynamoDB growth
- 90-day retention on global stats for historical analysis
- 7-day retention on session stats (sessions are ephemeral anyway)
- Midnight UTC reset aligns with AWS billing day
