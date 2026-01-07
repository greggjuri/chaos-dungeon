# Chaos Dungeon - Architecture Decisions

## ADR-001: Use Claude Haiku 3 for DM

**Date**: 2025-01-01
**Status**: Superseded by ADR-009

### Context
We need to choose a Claude model for the DM functionality. Budget is constrained to $20/month.

### Decision
Use Claude Haiku 3 ($0.25/$1.25 per million tokens).

### Rationale
- Cheapest Claude model available
- Still capable of creative narrative generation
- Budget allows ~10,000 player actions/month
- Can upgrade to Haiku 3.5 or Sonnet later if needed

### Consequences
- May have slightly less sophisticated responses than Sonnet
- Need to optimize prompts for quality within Haiku's capabilities
- Cost monitoring is critical

---

## ADR-002: AWS Serverless Architecture

**Date**: 2025-01-01  
**Status**: Accepted

### Context
Need to choose infrastructure approach for hosting the game.

### Decision
Use AWS serverless stack: Lambda + API Gateway + DynamoDB + S3/CloudFront.

### Rationale
- Pay-per-use aligns with budget constraints
- Lambda free tier: 1M requests/month
- DynamoDB on-demand: only pay for actual usage
- No server management overhead
- Good CDK support for IaC

### Consequences
- Cold start latency for Lambda
- Need to handle Lambda timeouts (max 15 min, but we'll use shorter)
- Vendor lock-in to AWS

---

## ADR-003: D&D BECMI Rules System

**Date**: 2025-01-01  
**Status**: Accepted

### Context
Need to choose a rules system for the RPG mechanics.

### Decision
Use D&D 1983 BECMI (Basic, Expert, Companion, Master) rules.

### Rationale
- Simpler than modern D&D, easier to implement
- Public domain/OGL considerations less complex
- Clear progression system (levels 1-36)
- Four classic classes for MVP
- Personal familiarity with the system

### Consequences
- Need to implement THAC0 → ascending AC conversion
- Spell system more limited than 5e
- Some rules modernization needed for UX

---

## ADR-004: Single-Table DynamoDB Design

**Date**: 2025-01-01  
**Status**: Accepted

### Context
Need to design database schema for game state.

### Decision
Use single-table design with composite keys:
- PK: `USER#{user_id}`
- SK: `CHAR#{character_id}` or `SESS#{session_id}`

### Rationale
- Efficient queries for user's characters/sessions
- Lower DynamoDB costs (fewer tables)
- Common pattern for serverless apps
- Flexible for future expansion

### Consequences
- More complex query patterns
- Need careful SK design for access patterns
- May need GSIs for some queries

---

## ADR-005: Anonymous Sessions for MVP

**Date**: 2025-01-01  
**Status**: Proposed

### Context
Need to decide on authentication strategy.

### Decision
Use anonymous sessions (localStorage-based user IDs) for MVP.

### Rationale
- Faster to implement
- Lower friction for new users
- Can add Cognito later for account features
- Sufficient for single-player experience

### Consequences
- Users lose data if they clear localStorage
- No cross-device sync
- Need migration path to Cognito later

---

## ADR-006: Prompt Caching Strategy

**Date**: 2025-01-01  
**Status**: Accepted

### Context
Need to minimize Claude API costs.

### Decision
Implement aggressive prompt caching:
- Cache system prompts (DM instructions, BECMI rules)
- Cache world/location descriptions
- Only send dynamic content (recent messages, current state)

### Rationale
- Prompt caching saves 90% on cached tokens
- System prompt is ~2000+ tokens, reused every request
- Significant cost reduction over time

### Consequences
- Need to structure prompts for optimal caching
- Must track cache breakpoints
- Slightly more complex prompt construction

---

## ADR-007: Mature Content Approach

**Date**: 2025-01-01  
**Status**: Accepted

### Context
Game is designed for mature, graphic content.

### Decision
Enable violent/dark fantasy content in DM system prompt, with:
- Age verification gate on first visit
- Content stored client-side (not moderated)
- Clear terms of service

### Rationale
- Target audience expects mature D&D-style content
- Adds to immersion for horror/dark fantasy themes
- User choice respected

### Consequences
- Must have clear age verification
- Terms of service required
- Not suitable for all audiences
- Consider content warnings per session

---

## ADR-008: React + Vite Frontend

**Date**: 2025-01-01  
**Status**: Accepted

### Context
Need to choose frontend framework and tooling.

### Decision
Use React 18 + TypeScript + Vite + Tailwind CSS.

### Rationale
- React: widely known, good ecosystem
- TypeScript: type safety, better DX
- Vite: fast builds, modern tooling
- Tailwind: rapid UI development, small bundle

### Consequences
- Slight learning curve for Tailwind
- Need to manage React 18 concurrent features
- Good mobile support with Tailwind

---

## ADR-009: Switch from Claude Haiku to Mistral Small for DM

**Date**: 2025-01-04
**Status**: Accepted
**Supersedes**: ADR-001

### Context

Testing revealed that Claude Haiku 3 has hard-coded content restrictions that cannot be overridden via system prompts. Despite extensive prompt engineering including:

- Explicit 18+ adult content permissions
- Strong fictional framing ("you are playing a character")
- Direct instructions to never refuse or break character
- Concrete examples of expected behavior

Haiku still refuses to:
- Narrate explicit sexual content (even mild physical contact like kissing)
- Depict violence against non-combatant NPCs
- Stay in character when content boundaries are approached

Additionally, Haiku exhibits problematic behavior:
- Breaks character to lecture about "appropriate boundaries"
- Halluccinates player responses to redirect narrative toward PG-13 content
- Inconsistent enforcement (allows seduction dialogue but refuses physical acts)

This fundamentally undermines the game's design as an adults-only dark fantasy experience where mature content is integral to immersion.

### Decision

Replace Claude Haiku 3 with **Mistral Small** via AWS Bedrock for the Dungeon Master AI.

### Alternatives Considered

| Model | Pricing | Content Flexibility | Quality | Verdict |
|-------|---------|---------------------|---------|---------|
| Claude Haiku 3 | $0.25/$1.25 per M | Poor - hard restrictions | Good | Current, failing |
| Claude Sonnet 4 | $3/$15 per M | Moderate | Excellent | 10x cost, may still refuse |
| Mistral Small | $1/$3 per M | Good - fewer guardrails | Good | **Selected** |
| Mistral Large | $4/$12 per M | Good | Excellent | 4x cost of Small |
| Llama 3.1 8B | $0.3/$0.6 per M | Excellent - minimal guardrails | Moderate | Quality concerns |
| Llama 3.1 70B | $2.6/$3.5 per M | Excellent | Good | Higher cost |

**Why Mistral Small:**
1. **Cost-effective**: ~$1/$3 per million tokens vs Haiku's $0.25/$1.25 - slightly more expensive but within budget
2. **Content flexibility**: Mistral models have significantly fewer content restrictions
3. **Quality**: Good narrative generation, comparable to Haiku for creative writing
4. **Bedrock integration**: Same AWS infrastructure, minimal code changes
5. **Proven**: Used successfully in other mature content applications

### Implementation

1. Update `backend/lambdas/action/handler.py` to use Bedrock Mistral client
2. Adjust system prompt format for Mistral's expected structure
3. Update prompt caching strategy (Mistral has different caching behavior)
4. Update CDK to add Bedrock Mistral model access
5. Test mature content scenarios that previously failed

### Code Changes Required

```python
# Before (Claude via Anthropic API)
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-3-haiku-20240307",
    ...
)

# After (Mistral via Bedrock)
import boto3
bedrock = boto3.client('bedrock-runtime')
response = bedrock.invoke_model(
    modelId="mistral.mistral-small-2402-v1:0",
    body=json.dumps({
        "prompt": formatted_prompt,
        "max_tokens": 1024,
        ...
    })
)
```

### Cost Impact

**Previous estimate (Haiku):**
- ~10,000 actions/month at ~2000 tokens/action
- Input: 20M tokens × $0.25/M = $5
- Output: 5M tokens × $1.25/M = $6.25
- **Total: ~$11/month**

**New estimate (Mistral Small):**
- Same usage pattern
- Input: 20M tokens × $1/M = $20
- Output: 5M tokens × $3/M = $15
- **Total: ~$35/month** ❌ Over budget

**Mitigation strategies:**
1. Reduce system prompt size (currently ~2200 tokens)
2. Implement response length limits
3. Aggressive prompt caching
4. Consider Llama 3.1 8B for non-narrative tasks

**Revised estimate with optimizations:**
- Reduce system prompt to ~1000 tokens
- Cache aggressively (90% cache hit rate)
- Limit responses to 500 tokens average
- **Target: ~$15-20/month** ✓

### Consequences

**Positive:**
- Mature content works as designed
- No more character-breaking refusals
- Consistent player experience
- Still within (optimized) budget

**Negative:**
- Slightly higher base cost per token
- Different prompt format required
- Lose Anthropic-specific features (prompt caching may differ)
- Need to test narrative quality matches Haiku
- May need further optimization to hit budget

**Risks:**
- Mistral quality may be lower for complex narrative
- Bedrock Mistral pricing could change
- May need fallback plan if Mistral also has issues

### Rollback Plan

If Mistral proves unsuitable:
1. Try Llama 3.1 70B (higher quality, similar flexibility)
2. Try Llama 3.1 8B (cheapest, test quality)
3. Hybrid approach: Mistral for RP, Claude for mechanics
4. Accept content limitations and adjust game design

### References

- [AWS Bedrock Mistral Models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-mistral.html)
- [Mistral AI Documentation](https://docs.mistral.ai/)
- Testing transcript showing Haiku failures (2025-01-04)

---

## ADR-010: Application-Level Cost Protection

**Date**: 2026-01-07
**Status**: Accepted

### Context

AWS Budget alerts have up to 6-hour delay before triggering, which is insufficient to prevent runaway AI costs in real-time. With Mistral Small pricing ($1/$3 per 1M tokens) and a $20/month budget, a compromised session or abuse scenario could consume the entire monthly budget before AWS Budgets reacts.

### Decision

Implement application-level token tracking using DynamoDB atomic counters with:
- **Global daily limit**: 500,000 tokens/day (~$1.10/day worst case)
- **Per-session daily limit**: 50,000 tokens/session/day
- **Pre-request limit checks** before calling Bedrock
- **Post-response usage recording** with atomic counters
- **In-game narrative messages** when limits are hit
- **CloudWatch metrics** for monitoring

### Implementation

1. `lambdas/shared/cost_limits.py` - Configuration constants
2. `lambdas/shared/token_tracker.py` - DynamoDB atomic counter operations
3. `lambdas/shared/cost_guard.py` - Limit checking before AI calls
4. DM handler checks limits before AI invocation, returns 429 with narrative
5. DM service records usage after successful responses
6. CloudWatch alarms for high usage (80%) and limit hits

### DynamoDB Schema

```
# Global daily usage
PK: USAGE#GLOBAL
SK: DATE#2026-01-07
TTL: 90 days

# Per-session daily usage
PK: SESSION#{session_id}
SK: USAGE#DATE#2026-01-07
TTL: 7 days
```

### Rationale

- DynamoDB atomic counters are thread-safe for concurrent requests
- Pre-request checks prevent wasted API calls
- In-game narrative messages maintain immersion when limits hit
- TTL enables automatic cleanup without maintenance
- CloudWatch metrics enable cost monitoring dashboards

### Consequences

**Positive:**
- Real-time budget protection (no 6-hour delay)
- Graceful degradation with themed messages
- Automatic daily reset at midnight UTC
- Self-cleaning via TTL
- Observable via CloudWatch

**Negative:**
- Slight DynamoDB latency for limit checks (~10ms)
- Additional AWS costs (~$0.52/month)
- Token estimation for Mistral (no exact counts from API)

### References

- PRP: `prps/prp-10-cost-protection.md`
- Init spec: `initials/init-10-cost-protection.md`

---

## ADR-011: Single Domain Architecture for Hosting

**Date**: 2026-01-07
**Status**: Accepted

### Context

The game needs to be deployed to production at `chaos.jurigregg.com`. Two architecture options were considered:

1. **Split Domain**: Frontend at `chaos.jurigregg.com`, API at `api.chaos.jurigregg.com`
2. **Single Domain**: Frontend at `chaos.jurigregg.com/`, API at `chaos.jurigregg.com/api/*`

### Decision

Use single domain architecture where CloudFront serves both frontend (from S3) and API (proxied to API Gateway) on the same domain.

### Rationale

- **No CORS**: Same-origin requests eliminate CORS complexity
- **Simpler Setup**: One CloudFront distribution, one DNS record
- **Cost Efficient**: Single distribution is cheaper than separate API Gateway custom domain
- **Better UX**: All requests go through CloudFront edge locations

### Implementation

- CloudFront distribution with two origins:
  - Default behavior (`/*`): S3 bucket for static frontend files
  - Path pattern (`/api/*`): API Gateway origin with path rewrite
- Route 53 A/AAAA alias records pointing to CloudFront
- Existing wildcard certificate (`*.jurigregg.com`) for SSL/TLS
- S3 bucket with OAC (Origin Access Control) - no public access

### Consequences

**Positive:**
- Simplified frontend API calls (relative paths)
- Single SSL certificate suffices
- All traffic benefits from CloudFront caching/edge

**Negative:**
- API paths must be prefixed with `/api` in CloudFront (path rewrite handled)
- Cannot independently scale frontend vs API CDN (minor concern)

### References

- PRP: `prps/prp-11-domain-setup.md`
- Init spec: `initials/init-11-domain-setup.md`

---

## Template for New Decisions

```markdown
## ADR-XXX: Title

**Date**: YYYY-MM-DD  
**Status**: Proposed/Accepted/Deprecated/Superseded

### Context
What is the issue that we're seeing that is motivating this decision?

### Decision
What is the change that we're proposing and/or doing?

### Rationale
Why is this the best choice? What alternatives were considered?

### Consequences
What becomes easier or more difficult because of this change?
```
