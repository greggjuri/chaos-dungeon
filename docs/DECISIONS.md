# Chaos Dungeon - Architecture Decisions

## ADR-001: Use Claude Haiku 3 for DM

**Date**: 2025-01-01  
**Status**: Accepted

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
