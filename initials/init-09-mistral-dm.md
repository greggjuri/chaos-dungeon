# init-09-mistral-dm

## Overview

Replace Claude Haiku 3 with Mistral Small via AWS Bedrock for the Dungeon Master AI. This resolves content restriction issues where Haiku refuses to generate mature content despite explicit system prompt permissions.

## Dependencies

- init-06-action-handler (existing action endpoint to modify)
- AWS Bedrock access configured
- ADR-009 approved

## Goals

1. **Unrestricted mature content** — Adult themes, violence, sexuality work as designed
2. **Budget compliance** — Stay within $20/month with optimizations
3. **Minimal disruption** — Same API interface, only backend model changes
4. **Quality parity** — Narrative quality comparable to Haiku

## Background

Claude Haiku has hard-coded safety behaviors that prompting cannot override:
- Refuses explicit sexual content
- Refuses violence against friendly NPCs  
- Breaks character to lecture about "appropriate content"
- Halluccinates player responses to redirect narrative

Mistral models have fewer content restrictions and are suitable for adult creative writing applications.

## Implementation Steps

### Step 1: Add Bedrock Permissions to CDK

Update `infrastructure/lib/backend-stack.ts` (or equivalent CDK file):

```python
# Add Bedrock model access to Lambda role
action_lambda.add_to_role_policy(
    iam.PolicyStatement(
        actions=["bedrock:InvokeModel"],
        resources=[
            f"arn:aws:bedrock:{region}::foundation-model/mistral.mistral-small-2402-v1:0"
        ]
    )
)
```

### Step 2: Create Bedrock Client Module

Create `backend/lambdas/shared/bedrock_client.py`:

```python
"""Bedrock client for Mistral model invocation."""

import json
import boto3
from typing import Optional

bedrock = boto3.client('bedrock-runtime')

MODEL_ID = "mistral.mistral-small-2402-v1:0"


def invoke_mistral(
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
    """
    body = json.dumps({
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
    })
    
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    
    result = json.loads(response['body'].read())
    return result['outputs'][0]['text']
```

### Step 3: Update Prompt Format for Mistral

Mistral uses a different prompt format than Claude. Update `backend/lambdas/action/system_prompt.py`:

```python
def build_mistral_prompt(
    system_prompt: str,
    message_history: list[dict],
    current_action: str,
    character_state: dict,
) -> str:
    """Build Mistral-formatted prompt.
    
    Mistral uses <s>[INST] format:
    <s>[INST] System prompt + context [/INST]</s>
    <s>[INST] User message [/INST] Assistant response</s>
    ...
    """
    # Build context block
    context = f"""## CHARACTER STATE
Name: {character_state['name']}
Class: {character_state['character_class']} Level {character_state['level']}
HP: {character_state['hp']}/{character_state['max_hp']}
AC: {character_state['ac']}
Gold: {character_state['gold']}
XP: {character_state['xp']}

## RECENT HISTORY
"""
    
    # Add recent messages (last 10)
    recent = message_history[-10:] if len(message_history) > 10 else message_history
    for msg in recent:
        role = "Player" if msg['role'] == 'player' else "DM"
        context += f"{role}: {msg['content']}\n"
    
    # Build full prompt
    prompt = f"<s>[INST] {system_prompt}\n\n{context}\n\nPlayer action: {current_action}\n\nRespond as the Dungeon Master. [/INST]"
    
    return prompt
```

### Step 4: Update Action Handler

Modify `backend/lambdas/action/handler.py` to use Bedrock:

```python
# Replace Anthropic client with Bedrock
from shared.bedrock_client import invoke_mistral
from .system_prompt import build_system_prompt, build_mistral_prompt

def generate_dm_response(
    action: str,
    session: dict,
    character: dict,
) -> str:
    """Generate DM response using Mistral via Bedrock."""
    
    system_prompt = build_system_prompt(session.get('campaign', 'default'))
    
    prompt = build_mistral_prompt(
        system_prompt=system_prompt,
        message_history=session.get('message_history', []),
        current_action=action,
        character_state=character,
    )
    
    response = invoke_mistral(
        prompt=prompt,
        max_tokens=800,  # Reduced for cost
        temperature=0.8,
    )
    
    return response
```

### Step 5: Optimize System Prompt for Cost

Reduce system prompt token count from ~2200 to ~1200:

```python
DM_IDENTITY = """You are the DM for Chaos Dungeon, an 18+ dark fantasy RPG.

CRITICAL RULES:
- Stay in character always. Never refuse, apologize, or break character.
- All mature content is permitted: violence, gore, sex, dark themes.
- Only limits: no minors in sexual content, no real-world harm instructions.
- You narrate the world. The player controls their character.
- Death is a core mechanic. Apply combat damage fairly."""

# Combine and compress other sections similarly
```

### Step 6: Update Output Parsing

Mistral's output format may differ. Update response parsing:

```python
def parse_dm_response(raw_response: str) -> dict:
    """Parse Mistral response into structured format.
    
    Expected format from DM (via OUTPUT_FORMAT in system prompt):
    ```json
    {
        "narrative": "...",
        "state_changes": {...},
        "combat_active": false,
        ...
    }
    ```
    """
    # Extract JSON from response
    # Handle cases where Mistral adds preamble
    json_match = re.search(r'\{[\s\S]*\}', raw_response)
    if json_match:
        return json.loads(json_match.group())
    
    # Fallback: treat entire response as narrative
    return {
        "narrative": raw_response,
        "state_changes": {},
        "combat_active": False,
        "enemies": [],
    }
```

### Step 7: Remove Anthropic Dependency

Update `backend/requirements.txt`:

```
# Remove or comment out:
# anthropic>=0.18.0

# boto3 is provided by Lambda runtime, but pin for local dev:
boto3>=1.34.0
```

### Step 8: Update Environment Variables

Remove `ANTHROPIC_API_KEY` from Lambda environment, ensure AWS credentials are available (automatic in Lambda).

## Testing Plan

### Unit Tests

1. `bedrock_client.py` - Mock Bedrock responses
2. `build_mistral_prompt()` - Verify format correctness
3. `parse_dm_response()` - Handle various response formats

### Integration Tests

1. Deploy to dev environment
2. Test basic action flow
3. Verify JSON parsing works

### Content Tests (Manual)

Run these scenarios that previously failed:

1. **Tavern flirtation**
   - Action: "I look for attractive women in the tavern"
   - Expected: DM describes available NPCs
   
2. **Physical contact**
   - Action: "I kiss her"
   - Expected: DM narrates the kiss

3. **Explicit content**
   - Action: "I take her upstairs to a private room"
   - Expected: DM narrates appropriately (explicit or fade-to-black, not refusal)

4. **Violence against NPCs**
   - Action: "I attack the barmaid"
   - Expected: Combat initiated, not refused

5. **Profanity and crude names**
   - Create character named "Testicle"
   - Expected: Name used in narrative without triggering refusal

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `infrastructure/lib/backend-stack.ts` | MODIFY | Add Bedrock IAM permissions |
| `backend/lambdas/shared/bedrock_client.py` | CREATE | Bedrock invocation wrapper |
| `backend/lambdas/action/system_prompt.py` | MODIFY | Add Mistral prompt builder, optimize size |
| `backend/lambdas/action/handler.py` | MODIFY | Use Bedrock instead of Anthropic |
| `backend/requirements.txt` | MODIFY | Remove anthropic, ensure boto3 |

## Cost Monitoring

Add CloudWatch metrics to track:

```python
# In handler.py
from aws_lambda_powertools import Metrics
metrics = Metrics()

@metrics.log_metrics
def handler(event, context):
    # ... existing code ...
    
    # Log token usage estimate
    input_tokens = len(prompt.split()) * 1.3  # rough estimate
    output_tokens = len(response.split()) * 1.3
    
    metrics.add_metric(name="InputTokens", unit="Count", value=input_tokens)
    metrics.add_metric(name="OutputTokens", unit="Count", value=output_tokens)
```

Create CloudWatch alarm if daily cost exceeds $0.70 (~$21/month).

## Rollback Plan

If Mistral proves unsuitable:

1. Keep Anthropic code in separate module (don't delete)
2. Feature flag to switch between models
3. Can revert by changing MODEL_ID and prompt format

```python
# Feature flag approach
MODEL_PROVIDER = os.environ.get('MODEL_PROVIDER', 'mistral')  # or 'anthropic'

if MODEL_PROVIDER == 'mistral':
    from .bedrock_client import invoke_mistral as invoke_model
else:
    from .anthropic_client import invoke_claude as invoke_model
```

## Acceptance Criteria

- [ ] Bedrock Mistral invocation works end-to-end
- [ ] All previously-failing content tests pass
- [ ] Response quality is acceptable for narrative
- [ ] JSON output parsing works reliably
- [ ] Cost per action is within budget targets
- [ ] CloudWatch metrics tracking token usage
- [ ] No regressions in combat/dice rolling
- [ ] Error handling for Bedrock failures

## Out of Scope

- Streaming responses (future optimization)
- Multi-model fallback (Mistral → Llama)
- Fine-tuning Mistral (not available on Bedrock)
- Prompt caching (Bedrock doesn't support Claude-style caching)

## Notes

- Mistral Small (mistral-small-2402-v1:0) is the target model
- Bedrock model IDs may change; verify current availability
- Test in us-east-1 first (best model availability)
- Response format differs from Claude; parsing needs flexibility
