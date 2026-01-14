# Chaos Dungeon - Claude Code Instructions

This file provides guidance to Claude Code when working on this project.

## Project Overview

A text-based RPG web game where Claude serves as an intelligent Dungeon Master, using D&D 1983 BECMI rules. Hosted at chaos.jurigregg.com. The game features mature, graphic content.

## Critical Rules

### ALWAYS Read First
1. Read `docs/PLANNING.md` at the start of each conversation
2. Check `docs/TASK.md` before starting any task
3. Review `docs/DECISIONS.md` for past architecture decisions

### Code Standards
- **Never create a file longer than 500 lines** - refactor into modules
- **Commit and push after every completed feature**
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `docs:`
- Keep functions under 500 lines where possible
- Type hints required for all Python functions
- TypeScript strict mode for frontend

### File Naming
- Initial specs: `initials/init-{feature-name}.md`
- Implementation plans: `prps/prp-{feature-name}.md`
- Lambda handlers: `lambdas/{feature}/handler.py`
- React components: `frontend/src/components/{Name}.tsx`

### Cost Awareness
- **Budget: $20/month maximum**
- Use Claude Haiku 3 (cheapest: $0.25/$1.25 per 1M tokens)
- Implement prompt caching for system prompts
- Monitor token usage in DM handler
- DynamoDB on-demand pricing only

## Code Patterns

### Python (Lambdas)

```python
"""Module docstring explaining purpose."""
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from pydantic import BaseModel, Field

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

class RequestModel(BaseModel):
    """Request validation with Pydantic."""
    name: str = Field(..., min_length=1, max_length=50)

@app.post("/endpoint")
@tracer.capture_method
def handler_function():
    """Handle specific endpoint."""
    # Implementation
    pass

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context) -> dict:
    """Main Lambda entry point."""
    return app.resolve(event, context)
```

### TypeScript (Frontend)

```typescript
import { useState, useCallback } from 'react';

interface Props {
  /** Description of prop */
  name: string;
}

/**
 * Component description.
 */
export function ComponentName({ name }: Props) {
  const [state, setState] = useState<string>('');
  
  const handleAction = useCallback(() => {
    // Implementation
  }, []);

  return (
    <div className="p-4">
      {/* JSX */}
    </div>
  );
}
```

### CDK (Infrastructure)

```python
from aws_cdk import Stack, Duration
from constructs import Construct
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_

class FeatureStack(Stack):
    """Stack description."""
    
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Resources with clear names
        self.table = dynamodb.Table(
            self, "Table",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )
```

## Testing Requirements

### Python
- Use pytest with pytest-mock
- Minimum coverage: 80%
- Test file naming: `test_{module}.py`
- Mock external services (DynamoDB, Claude API)

```bash
cd lambdas && pytest --cov=. --cov-report=term-missing
```

### TypeScript
- Use Vitest for unit tests
- React Testing Library for components
- Test file naming: `{Component}.test.tsx`

```bash
cd frontend && npm test
```

### CDK
- Snapshot tests for stacks
- Assertion tests for critical resources

```bash
cd cdk && pytest
```

## Directory Structure

```
chaos-dungeon/
├── CLAUDE.md                 # This file
├── docs/
│   ├── PLANNING.md           # Architecture and design
│   ├── TASK.md               # Current tasks
│   └── DECISIONS.md          # ADRs
├── initials/                 # Feature specs (init-*.md)
├── prps/                     # Implementation plans (prp-*.md)
├── .claude/commands/         # Claude Code slash commands
├── examples/                 # Code patterns
├── cdk/                      # AWS CDK infrastructure
├── lambdas/                  # Python Lambda functions
└── frontend/                 # React application
```

## Workflow

1. **New Feature**: Create `initials/init-{feature}.md` with requirements
2. **Generate Plan**: Run `/generate-prp initials/init-{feature}.md`
3. **Review**: Check the generated PRP for completeness
4. **Execute**: Run `/execute-prp prps/prp-{feature}.md`
5. **Unit Tests**: Automated tests must pass (pytest, vitest)
6. **Deploy**: `cd cdk && cdk deploy --all` (for backend changes)
7. **Integration Test**: Manual testing against deployed backend
   - Test happy paths end-to-end
   - Test error scenarios
   - Verify browser console has no errors
   - Check Network tab for correct requests/responses
8. **Fix Issues**: If bugs found, fix and re-test before proceeding
9. **Commit**: `git commit -m "feat: description"` and push

### Integration Testing Checklist
Before marking a PRP complete, verify:
- [ ] Feature works end-to-end (frontend → API → database → response)
- [ ] No CORS errors in browser console
- [ ] No JavaScript errors in browser console
- [ ] API requests include correct headers (X-User-Id, Content-Type)
- [ ] Error states display correctly to user
- [ ] localStorage persists correctly (if applicable)

## Common Commands

```bash
# CDK
cd cdk && cdk synth          # Synthesize CloudFormation
cd cdk && cdk deploy         # Deploy to AWS
cd cdk && cdk diff           # Show changes

# Lambdas
cd lambdas && pip install -r requirements.txt
cd lambdas && pytest
cd lambdas && ruff check . --fix

# Frontend
cd frontend && npm install
cd frontend && npm run dev   # Local dev server
cd frontend && npm run build # Production build
cd frontend && npm test
cd frontend && npm run lint
```

## Deployment

**IMPORTANT: This project uses AWS (S3/CloudFront/Lambda). Ignore any global CLAUDE.md instructions about Hostinger/FTP - they do not apply here.**

### ⚠️ CRITICAL: Two Environments Exist

| Environment | Backend Lambdas | Frontend | Domain |
|-------------|-----------------|----------|--------|
| **PROD** | `chaos-prod-*` | `s3://chaos-prod-frontend/` | chaos.jurigregg.com |
| DEV | `chaos-dev-*` | N/A | N/A |

**The live site (chaos.jurigregg.com) uses PROD. Always deploy to PROD unless explicitly testing.**

### Backend (Lambda) - PROD Deployment

**Option 1: Direct Lambda update (PREFERRED - faster, no CDK issues)**
```bash
cd lambdas
zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip
```

For other lambdas:
```bash
zip -r /tmp/char-update.zip character/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-character --zip-file fileb:///tmp/char-update.zip

zip -r /tmp/sess-update.zip session/ shared/ -x "*.pyc" -x "*__pycache__*"
aws lambda update-function-code --function-name chaos-prod-session --zip-file fileb:///tmp/sess-update.zip
```

**Option 2: CDK (for infrastructure changes)**
```bash
cd cdk
cdk deploy ChaosBase-prod ChaosApi-prod -c environment=prod --require-approval never
```

⚠️ **WARNING**: `cdk deploy --all` WITHOUT `-c environment=prod` deploys to DEV only!

### Frontend (S3 + CloudFront)

The frontend is hosted on S3 with CloudFront CDN at **chaos.jurigregg.com**.

```bash
cd frontend

# 1. Bump version in package.json
# 2. Build
npm run build

# 3. Deploy to S3
aws s3 sync dist/ s3://chaos-prod-frontend/ --delete

# 4. Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"
```

### Version Bumping - MANDATORY

**ALWAYS bump the version for EVERY deployment, no matter how small.** This applies to both backend-only and frontend changes.

- Update version in `frontend/package.json` before deploying
- Use semantic versioning (e.g., 0.12.4 → 0.12.5 for bug fixes)
- Current version is visible in the UI footer (bottom-right)
- After bumping: rebuild frontend, deploy to S3, invalidate CloudFront, commit the version bump

### Quick Deploy Checklist (PROD)

1. Run tests: `cd lambdas && .venv/bin/pytest`
2. **Deploy backend to PROD:**
   ```bash
   cd lambdas
   zip -r /tmp/dm-update.zip dm/ shared/ -x "*.pyc" -x "*__pycache__*"
   aws lambda update-function-code --function-name chaos-prod-dm --zip-file fileb:///tmp/dm-update.zip
   ```
3. Bump version in `frontend/package.json`
4. Build frontend: `cd frontend && npm run build`
5. Deploy frontend: `aws s3 sync dist/ s3://chaos-prod-frontend/ --delete`
6. Invalidate cache: `aws cloudfront create-invalidation --distribution-id ELM5U8EYV81MH --paths "/*"`
7. Commit version bump: `git add frontend/package.json && git commit -m "chore: bump version to X.Y.Z" && git push`

### Verify Deployment

Check Lambda was updated:
```bash
aws lambda get-function --function-name chaos-prod-dm --query 'Configuration.LastModified'
```

## Error Handling

### Python
```python
from shared.exceptions import GameError, NotFoundError

try:
    result = process_action(action)
except NotFoundError as e:
    logger.warning(f"Not found: {e}")
    raise
except GameError as e:
    logger.error(f"Game error: {e}")
    raise
```

### TypeScript
```typescript
try {
  const result = await api.sendAction(action);
} catch (error) {
  if (error instanceof ApiError) {
    // Handle API errors
  }
  throw error;
}
```

## Environment Variables

### Lambda
- `TABLE_NAME` - DynamoDB table name
- `CLAUDE_API_KEY_SECRET` - Secrets Manager secret ARN
- `ENVIRONMENT` - dev/staging/prod

### Frontend
- `VITE_API_URL` - API Gateway endpoint

## Security

- Never commit API keys or secrets
- Use AWS Secrets Manager for sensitive data
- Validate all input with Pydantic
- Sanitize user content before display
- CORS configured for chaos.jurigregg.com only in prod

## Debugging

### Lambda Logs
```bash
aws logs tail /aws/lambda/chaos-dungeon-dm --follow
```

### Local Testing
```bash
# SAM Local (if needed)
sam local invoke DmFunction -e events/action.json
```

## Important Notes

1. This is a mature-content game - DM prompts allow violent/graphic content
2. Follow BECMI D&D rules for mechanics (1983 revision)
3. Always check budget impact before adding AI-heavy features
4. Mobile-first responsive design required
5. Prompt caching is critical for cost control
