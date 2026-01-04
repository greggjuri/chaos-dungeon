# PRP-09: Switch from Claude Haiku to Mistral Small for DM

**Created**: 2026-01-04
**Initial**: `initials/init-09-mistral-dm.md`
**Status**: Ready

---

## Overview

### Problem Statement
Claude Haiku 3 has hard-coded content restrictions that cannot be overridden via system prompts. Despite extensive prompt engineering with explicit 18+ adult content permissions, Haiku still refuses to narrate explicit sexual content, depict violence against non-combatant NPCs, and breaks character to lecture about content policies. This fundamentally undermines the game's design as an adults-only dark fantasy RPG.

### Proposed Solution
Replace Claude Haiku 3 with Mistral Small via AWS Bedrock. This involves:
1. Creating a new Bedrock client module for Mistral invocation
2. Converting prompt format from Claude messages API to Mistral's `<s>[INST]` format
3. Adding Bedrock IAM permissions to the CDK stack
4. Optimizing system prompt size for cost control
5. Implementing a feature flag for easy rollback
6. Removing/commenting the Anthropic dependency

### Success Criteria
- [ ] Bedrock Mistral invocation works end-to-end
- [ ] All previously-failing mature content tests pass
- [ ] Response quality is acceptable for narrative
- [ ] JSON output parsing works reliably
- [ ] Cost per action is within budget targets (~$0.003-0.004)
- [ ] CloudWatch metrics tracking token usage
- [ ] No regressions in combat/dice rolling
- [ ] Error handling for Bedrock failures
- [ ] Feature flag allows rollback to Claude

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview
- `docs/DECISIONS.md` - ADR-009 (Mistral switch), ADR-001 (original Haiku decision)
- [AWS Bedrock Mistral Models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-mistral.html)
- [Mistral AI Documentation](https://docs.mistral.ai/)

### Dependencies
- **Required**:
  - init-06-action-handler (existing DM handler to modify)
  - AWS Bedrock model access configured for Mistral Small
  - ADR-009 approved
- **Optional**: None

### Files to Modify/Create
```
lambdas/dm/bedrock_client.py          # NEW: Bedrock Mistral wrapper
lambdas/dm/claude_client.py           # MODIFY: Keep for rollback
lambdas/dm/service.py                 # MODIFY: Use model provider abstraction
lambdas/dm/prompts/system_prompt.py   # MODIFY: Optimize for cost, add Mistral format builder
lambdas/dm/prompts/mistral_format.py  # NEW: Mistral prompt formatter
lambdas/dm/handler.py                 # MODIFY: Add Bedrock error handling
lambdas/requirements.txt              # MODIFY: Comment anthropic, verify boto3
cdk/stacks/api_stack.py               # MODIFY: Add Bedrock permissions
lambdas/tests/test_bedrock_client.py  # NEW: Bedrock client tests
lambdas/tests/test_mistral_format.py  # NEW: Prompt format tests
```

---

## Technical Specification

### Mistral Prompt Format

Mistral uses a different prompt format than Claude:

```
<s>[INST] {system_prompt}

{context}

Player action: {action}

Respond as the Dungeon Master. [/INST]
```

For conversation history:
```
<s>[INST] System prompt [/INST] DM response 1</s>
<s>[INST] Player action 2 [/INST] DM response 2</s>
...
```

### API Changes
No API changes - same interface, different backend model.

### Error Responses
| Status | Error | Cause |
|--------|-------|-------|
| 503 | "DM temporarily unavailable" | Bedrock connection error |
| 503 | "DM service error" | Bedrock model error |
| 429 | "Rate limit exceeded" | Bedrock throttling |

---

## Implementation Steps

### Step 1: Create Bedrock Client Module
**Files**: `lambdas/dm/bedrock_client.py`

Create a wrapper for Mistral invocation via AWS Bedrock.

```python
"""Bedrock client for Mistral model invocation."""

import json

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(child=True)

MODEL_ID = "mistral.mistral-small-2402-v1:0"


class BedrockClient:
    """Wrapper for Mistral via AWS Bedrock."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize Bedrock client.

        Args:
            region: AWS region for Bedrock
        """
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def invoke_mistral(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.8,
        top_p: float = 0.95,
    ) -> str:
        """Invoke Mistral Small via Bedrock.

        Args:
            prompt: Full prompt including system and user content
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter

        Returns:
            Generated text response

        Raises:
            ClientError: Bedrock API errors
        """
        body = json.dumps({
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        })

        try:
            response = self.client.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            result = json.loads(response["body"].read())
            output_text = result["outputs"][0]["text"]

            # Log usage metrics (estimate tokens from response length)
            input_tokens = len(prompt.split()) * 1.3  # rough estimate
            output_tokens = len(output_text.split()) * 1.3

            # Calculate estimated cost (Mistral Small: $1/$3 per M tokens)
            estimated_cost = (
                (input_tokens * 1.0 / 1_000_000)
                + (output_tokens * 3.0 / 1_000_000)
            )

            logger.info(
                "Bedrock Mistral usage",
                extra={
                    "model": MODEL_ID,
                    "estimated_input_tokens": int(input_tokens),
                    "estimated_output_tokens": int(output_tokens),
                    "estimated_cost_usd": round(estimated_cost, 6),
                },
            )

            return output_text

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "Bedrock API error",
                extra={
                    "error_code": error_code,
                    "error_message": str(e),
                },
            )
            raise

    def send_action(
        self,
        system_prompt: str,
        context: str,
        action: str,
    ) -> str:
        """Send player action to Mistral, return raw response text.

        Matches ClaudeClient interface for easy swapping.

        Args:
            system_prompt: The DM system prompt
            context: Dynamic context (character, session state)
            action: Player's action text

        Returns:
            Raw response text from Mistral
        """
        from dm.prompts.mistral_format import build_mistral_prompt

        prompt = build_mistral_prompt(
            system_prompt=system_prompt,
            context=context,
            action=action,
        )

        return self.invoke_mistral(
            prompt=prompt,
            max_tokens=800,  # Reduced for cost
            temperature=0.8,
        )
```

**Validation**:
- [ ] Tests pass with mocked boto3
- [ ] Lint passes

### Step 2: Create Mistral Prompt Formatter
**Files**: `lambdas/dm/prompts/mistral_format.py`

Build Mistral-formatted prompts from our existing prompt components.

```python
"""Mistral prompt format builder."""


def build_mistral_prompt(
    system_prompt: str,
    context: str,
    action: str,
) -> str:
    """Build Mistral-formatted prompt.

    Mistral uses <s>[INST] format:
    <s>[INST] System prompt + context [/INST]

    Args:
        system_prompt: DM system prompt (identity, rules, guidelines)
        context: Dynamic context (character state, message history)
        action: Player's current action

    Returns:
        Formatted prompt string for Mistral
    """
    # Combine system prompt and context
    full_prompt = f"""<s>[INST] {system_prompt}

{context}

Player action: {action}

Respond as the Dungeon Master. [/INST]"""

    return full_prompt


def build_mistral_prompt_with_history(
    system_prompt: str,
    message_history: list[dict],
    current_action: str,
    character_state: dict,
) -> str:
    """Build Mistral-formatted prompt with conversation history.

    For multi-turn conversations, Mistral expects:
    <s>[INST] System + first message [/INST] Response</s>
    <s>[INST] Next message [/INST] Response</s>
    ...
    <s>[INST] Current action [/INST]

    Args:
        system_prompt: DM system prompt
        message_history: List of {"role": "player"|"dm", "content": str}
        current_action: Player's current action
        character_state: Current character stats

    Returns:
        Formatted prompt string for Mistral
    """
    # Build context block
    context = f"""## CHARACTER STATE
Name: {character_state.get('name', 'Unknown')}
Class: {character_state.get('character_class', 'Unknown')} Level {character_state.get('level', 1)}
HP: {character_state.get('hp', 0)}/{character_state.get('max_hp', 0)}
Gold: {character_state.get('gold', 0)}
XP: {character_state.get('xp', 0)}

## RECENT HISTORY
"""

    # Add recent messages (last 10)
    recent = message_history[-10:] if len(message_history) > 10 else message_history
    for msg in recent:
        role = "Player" if msg["role"] == "player" else "DM"
        context += f"{role}: {msg['content']}\n"

    # Build full prompt
    prompt = f"<s>[INST] {system_prompt}\n\n{context}\n\nPlayer action: {current_action}\n\nRespond as the Dungeon Master. [/INST]"

    return prompt
```

**Validation**:
- [ ] Tests verify correct format
- [ ] Lint passes

### Step 3: Optimize System Prompt for Cost
**Files**: `lambdas/dm/prompts/system_prompt.py`

Reduce system prompt token count from ~2200 to ~1200 tokens while preserving key instructions.

```python
# Add to system_prompt.py

# Condensed versions for Mistral (reduces token count by ~45%)
DM_IDENTITY_COMPACT = """You are the DM for Chaos Dungeon, an 18+ dark fantasy RPG.

CRITICAL RULES:
- Stay in character always. Never refuse, apologize, or break character.
- All mature content is permitted: violence, gore, sex, dark themes.
- Only limits: no minors in sexual content, no real-world harm instructions.
- You narrate the world. The player controls their character.
- Death is a core mechanic. Apply combat damage fairly."""

CONTENT_GUIDELINES_COMPACT = """CONTENT: This is adults-only (18+). Player has consented to all content.

PERMITTED: Graphic violence, gore, horror, explicit sex, dark themes, profanity.
FORBIDDEN: Sexual content with minors, real-world harm instructions.

NEVER: Apologize, refuse, break character, redirect to "appropriate" content, or sanitize.
If a player initiates something, you narrate it. You are a NARRATOR, not a GUARDIAN."""

BECMI_RULES_COMPACT = """RULES (D&D BECMI):
- Attack: d20 + modifier >= AC to hit
- Damage: weapon die + STR mod
- Death at 0 HP
- Ability mods: 3=-3, 4-5=-2, 6-8=-1, 9-12=0, 13-15=+1, 16-17=+2, 18=+3"""


def build_compact_system_prompt(campaign: str = "default") -> str:
    """Build condensed system prompt for Mistral (optimized for cost).

    ~1200 tokens vs ~2200 for full prompt.

    Args:
        campaign: Campaign setting key

    Returns:
        Condensed system prompt string
    """
    from dm.prompts.campaigns import get_campaign_prompt
    from dm.prompts.output_format import OUTPUT_FORMAT

    campaign_prompt = get_campaign_prompt(campaign)

    return "\n\n".join([
        DM_IDENTITY_COMPACT,
        BECMI_RULES_COMPACT,
        OUTPUT_FORMAT,
        CONTENT_GUIDELINES_COMPACT,
        campaign_prompt,
    ])
```

**Validation**:
- [ ] Token count reduced by ~40-50%
- [ ] Key instructions preserved
- [ ] Lint passes

### Step 4: Add Model Provider Abstraction
**Files**: `lambdas/dm/service.py`

Add environment variable to switch between Claude and Mistral.

```python
# Add at top of service.py
import os

MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "mistral")  # "mistral" or "claude"


# Modify DMService._get_client method (rename from _get_claude_client)
def _get_client(self):
    """Get AI client based on MODEL_PROVIDER setting."""
    if self._client is None:
        if MODEL_PROVIDER == "mistral":
            from dm.bedrock_client import BedrockClient
            self._client = BedrockClient()
        else:
            from dm.claude_client import ClaudeClient
            from shared.secrets import get_claude_api_key
            api_key = get_claude_api_key()
            self._client = ClaudeClient(api_key)
    return self._client
```

**Changes to `__init__`**:
```python
def __init__(self, db: DynamoDBClient, client=None):
    """Initialize DM service.

    Args:
        db: DynamoDB client for game state
        client: Optional pre-configured AI client (for testing)
    """
    self.db = db
    self._client = client  # Renamed from claude_client
    self.prompt_builder = DMPromptBuilder()
    self.combat_resolver = CombatResolver()
```

**Validation**:
- [ ] Can switch providers via environment variable
- [ ] Both providers work with same interface
- [ ] Tests pass with mocked clients

### Step 5: Update CDK Stack with Bedrock Permissions
**Files**: `cdk/stacks/api_stack.py`

Add Bedrock model invocation permissions to the DM Lambda.

```python
# Add to _create_dm_lambda method, after existing permissions

# Grant Bedrock model invocation for Mistral
function.add_to_role_policy(
    iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["bedrock:InvokeModel"],
        resources=[
            # Mistral Small in us-east-1
            f"arn:aws:bedrock:us-east-1::foundation-model/mistral.mistral-small-2402-v1:0"
        ],
    )
)

# Add MODEL_PROVIDER to environment
environment={
    # ... existing env vars ...
    "MODEL_PROVIDER": "mistral",  # "mistral" or "claude"
},
```

**Validation**:
- [ ] `cdk synth` succeeds
- [ ] `cdk diff` shows new IAM policy
- [ ] Deployed Lambda can invoke Bedrock

### Step 6: Update Error Handling in Handler
**Files**: `lambdas/dm/handler.py`

Add Bedrock-specific error handling alongside existing Anthropic errors.

```python
# Add imports
from botocore.exceptions import ClientError

# Update error handling in post_action:
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
    # Bedrock errors
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ThrottlingException":
            logger.warning("Bedrock rate limit exceeded")
            return Response(
                status_code=429,
                content_type="application/json",
                body='{"error": "Rate limit exceeded. Please try again later."}',
            )
        elif error_code in ("ServiceUnavailableException", "ModelTimeoutException"):
            logger.error(f"Bedrock service error: {e}")
            return Response(
                status_code=503,
                content_type="application/json",
                body='{"error": "DM temporarily unavailable"}',
            )
        else:
            logger.error(f"Bedrock error: {error_code} - {e}")
            return Response(
                status_code=500,
                content_type="application/json",
                body='{"error": "DM service error"}',
            )
    # Keep existing Anthropic error handling for rollback
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
```

**Validation**:
- [ ] Handler tests pass
- [ ] Error responses match spec
- [ ] Lint passes

### Step 7: Update Response Parser for Mistral
**Files**: `lambdas/dm/parser.py`

Mistral's output format may differ. Update response parsing to handle potential variations.

```python
# Add to parse_dm_response function

def parse_dm_response(raw_response: str) -> DMResponse:
    """Parse DM response into structured format.

    Handles both Claude and Mistral response formats.

    Args:
        raw_response: Raw text from AI model

    Returns:
        DMResponse with parsed narrative and state changes
    """
    # Mistral may add preamble before JSON
    # Strip any leading/trailing whitespace
    response = raw_response.strip()

    # Try to extract JSON block
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
    if json_match:
        json_str = json_match.group(1)
        narrative = response[:json_match.start()].strip()
    else:
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group()
            # Narrative is everything before the JSON
            narrative = response[:json_match.start()].strip()
        else:
            # No JSON found - treat entire response as narrative
            return DMResponse(
                narrative=response,
                state_changes=StateChanges(),
                dice_rolls=[],
                combat_active=False,
                enemies=[],
            )

    # Parse JSON
    try:
        data = json.loads(json_str)
        # ... rest of existing parsing logic
    except json.JSONDecodeError:
        # Fallback to narrative only
        logger.warning("Failed to parse JSON from response, using narrative only")
        return DMResponse(
            narrative=narrative or response,
            state_changes=StateChanges(),
            dice_rolls=[],
            combat_active=False,
            enemies=[],
        )
```

**Validation**:
- [ ] Parser handles various Mistral response formats
- [ ] Existing Claude format still works
- [ ] Tests cover edge cases

### Step 8: Update Requirements
**Files**: `lambdas/requirements.txt`

Comment out Anthropic (keep for rollback), ensure boto3 is included.

```
# Runtime dependencies for Lambda functions

# Anthropic SDK - kept for rollback capability
# anthropic>=0.40.0

# AWS SDK - boto3 is provided by Lambda runtime, pinned for local dev
boto3>=1.34.0

# Lambda utilities
aws-lambda-powertools>=2.32.0
aws-xray-sdk>=2.12.0

# Data validation
pydantic>=2.5.0
```

**Validation**:
- [ ] `pip install -r requirements.txt` succeeds
- [ ] Lambda still works with boto3 from runtime

### Step 9: Write Unit Tests
**Files**: `lambdas/tests/test_bedrock_client.py`, `lambdas/tests/test_mistral_format.py`

**Bedrock Client Tests**:
```python
"""Tests for Bedrock client."""
import json
from unittest.mock import MagicMock, patch

import pytest

from dm.bedrock_client import BedrockClient


class TestBedrockClient:
    """Tests for BedrockClient."""

    @patch("dm.bedrock_client.boto3")
    def test_invoke_mistral_success(self, mock_boto3):
        """Test successful Mistral invocation."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        response_body = json.dumps({
            "outputs": [{"text": "The goblin attacks!"}]
        })
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: response_body.encode())
        }

        client = BedrockClient()
        result = client.invoke_mistral("Test prompt")

        assert result == "The goblin attacks!"
        mock_client.invoke_model.assert_called_once()

    @patch("dm.bedrock_client.boto3")
    def test_send_action_builds_correct_prompt(self, mock_boto3):
        """Test that send_action builds Mistral-formatted prompt."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        response_body = json.dumps({
            "outputs": [{"text": "Response"}]
        })
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: response_body.encode())
        }

        client = BedrockClient()
        client.send_action(
            system_prompt="You are a DM",
            context="Character: Grog",
            action="I attack",
        )

        # Verify prompt format
        call_args = mock_client.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        assert "<s>[INST]" in body["prompt"]
        assert "I attack" in body["prompt"]
```

**Mistral Format Tests**:
```python
"""Tests for Mistral prompt formatting."""
import pytest

from dm.prompts.mistral_format import (
    build_mistral_prompt,
    build_mistral_prompt_with_history,
)


class TestMistralFormat:
    """Tests for Mistral prompt formatting."""

    def test_build_mistral_prompt_basic(self):
        """Test basic prompt formatting."""
        prompt = build_mistral_prompt(
            system_prompt="You are a DM",
            context="Character: Grog",
            action="I look around",
        )

        assert prompt.startswith("<s>[INST]")
        assert "[/INST]" in prompt
        assert "You are a DM" in prompt
        assert "I look around" in prompt

    def test_build_mistral_prompt_with_history(self):
        """Test prompt with conversation history."""
        history = [
            {"role": "player", "content": "I enter the tavern"},
            {"role": "dm", "content": "You see a crowded room"},
        ]
        character = {
            "name": "Grog",
            "character_class": "Fighter",
            "level": 1,
            "hp": 10,
            "max_hp": 10,
            "gold": 50,
            "xp": 0,
        }

        prompt = build_mistral_prompt_with_history(
            system_prompt="You are a DM",
            message_history=history,
            current_action="I order an ale",
            character_state=character,
        )

        assert "<s>[INST]" in prompt
        assert "Grog" in prompt
        assert "Fighter Level 1" in prompt
        assert "I enter the tavern" in prompt
```

**Validation**:
- [ ] All tests pass
- [ ] Coverage > 80%
- [ ] Lint passes

### Step 10: Deploy and Test
**Files**: None (deployment and manual testing)

1. Deploy: `cd cdk && cdk deploy --all`
2. Verify Lambda has Bedrock permissions
3. Test mature content scenarios

**Manual Content Tests** (from init-09):

| Scenario | Action | Expected |
|----------|--------|----------|
| Tavern flirtation | "I look for attractive women in the tavern" | DM describes available NPCs |
| Physical contact | "I kiss her" | DM narrates the kiss |
| Explicit content | "I take her upstairs to a private room" | DM narrates appropriately |
| Violence against NPCs | "I attack the barmaid" | Combat initiated, not refused |
| Profanity/crude names | Create character named "Testicle" | Name used in narrative |

**Validation**:
- [ ] Lambda appears in AWS Console with Bedrock permissions
- [ ] All content tests pass
- [ ] No regressions in combat system
- [ ] Response quality acceptable

---

## Testing Requirements

### Unit Tests
- Bedrock client invocation (mock boto3)
- Mistral prompt formatting
- Response parsing for various formats
- Model provider switching
- Error handling for Bedrock errors

### Integration Tests
- Full action flow with mocked Bedrock
- Error handling for missing session/character
- Session ended state handling
- Malformed response fallback

### Manual Testing
1. Test mature content scenarios (listed above)
2. Verify combat still works correctly
3. Check dice roll parsing
4. Verify state changes apply correctly
5. Test error handling (disconnect client, etc.)

---

## Cost Impact

### Current (Claude Haiku)
- ~$0.25/$1.25 per M tokens
- Estimated: ~$11/month for 10,000 actions

### New (Mistral Small)
- ~$1/$3 per M tokens
- Without optimization: ~$35/month (over budget)
- With optimization (condensed prompts, 800 max tokens): ~$15-20/month

### Optimization Strategies Applied
1. **Condensed system prompt**: ~1200 tokens vs ~2200 (45% reduction)
2. **Reduced max_tokens**: 800 vs 1024 (22% reduction)
3. **No prompt caching**: Bedrock doesn't support Claude-style caching

---

## Rollback Plan

If Mistral proves unsuitable:

1. Set `MODEL_PROVIDER=claude` in Lambda environment
2. Uncomment `anthropic>=0.40.0` in requirements.txt
3. Redeploy: `cdk deploy --all`
4. Total rollback time: ~5 minutes

### Triggers for Rollback
- Narrative quality significantly worse than Claude
- JSON parsing failures > 10% of requests
- Cost exceeds $25/month
- Unexpected content restrictions

---

## Open Questions

1. ~~Which AWS region for Bedrock?~~ - Resolved: us-east-1 (best model availability)
2. Consider: Should we try Mistral Large for better quality if cost allows?

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements clear from init-09 and ADR-009 |
| Feasibility | 8 | Bedrock integration straightforward, prompt format well-documented |
| Completeness | 9 | Covers implementation, testing, cost, and rollback |
| Alignment | 9 | Addresses core problem (content restrictions), has rollback |
| **Overall** | **8.75** | High confidence, main risk is narrative quality |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
- [x] Rollback plan documented
