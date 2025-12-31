# PRP-01: Project Foundation

**Created**: 2025-01-01
**Initial**: `initials/init-01-project-foundation.md`
**Status**: Complete

---

## Overview

### Problem Statement
The Chaos Dungeon project needs its foundational infrastructure before any game features can be built. This includes AWS resources (DynamoDB, Lambda layers), CDK stacks for infrastructure-as-code, and the React frontend scaffolding. Without this foundation, no subsequent features can be developed.

### Proposed Solution
Create a complete project foundation consisting of:
1. **CDK Infrastructure**: Two stacks (`ChaosBaseStack` and `ChaosApiStack`) managing all AWS resources
2. **Lambda Shared Layer**: Reusable Python code for database access, models, and utilities
3. **Frontend Shell**: React + TypeScript + Vite + Tailwind CSS scaffolding
4. **Testing Infrastructure**: pytest for Python, Vitest for TypeScript

### Success Criteria
- [ ] `cdk synth` succeeds without errors
- [ ] DynamoDB table created with PK/SK schema and GSI
- [ ] Lambda layer builds successfully with shared code
- [ ] Shared models can be imported in Lambda handlers
- [ ] Frontend dev server runs with `npm run dev`
- [ ] All Python tests pass with `pytest`
- [ ] All TypeScript tests pass with `npm test`
- [ ] Each file stays under 500 lines
- [ ] ruff linting passes for all Python code

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview and data models
- `docs/DECISIONS.md` - ADR-002 (AWS Serverless), ADR-004 (Single-Table), ADR-008 (React+Vite)
- [AWS CDK Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
- [DynamoDB Single Table](https://www.alexdebrie.com/posts/dynamodb-single-table/)
- [Lambda Powertools](https://docs.powertools.aws.dev/lambda/python/latest/)
- [Pydantic V2](https://docs.pydantic.dev/latest/)

### Dependencies
- **Required**: None - this is the first PRP
- **Optional**: None

### Files to Create
```
cdk/
├── app.py                    # CDK app entry point
├── cdk.json                  # CDK configuration
├── requirements.txt          # CDK Python dependencies
├── stacks/
│   ├── __init__.py
│   ├── base_stack.py         # DynamoDB, Secrets, Lambda layer
│   └── api_stack.py          # API Gateway, Lambda functions
└── tests/
    ├── __init__.py
    └── test_stacks.py        # CDK stack tests

lambdas/
├── requirements.txt          # Lambda runtime dependencies
├── requirements-dev.txt      # Dev/test dependencies
├── shared/
│   ├── __init__.py
│   ├── models.py             # Pydantic models (Character, Session, etc.)
│   ├── db.py                 # DynamoDB client wrapper
│   ├── exceptions.py         # Custom exception classes
│   ├── config.py             # Environment configuration
│   └── utils.py              # Utility functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # pytest fixtures
│   └── test_shared.py        # Shared module tests
└── pyproject.toml            # Python project config (ruff, pytest)

frontend/
├── package.json              # NPM dependencies and scripts
├── tsconfig.json             # TypeScript configuration
├── tsconfig.node.json        # Node TypeScript config
├── vite.config.ts            # Vite build configuration
├── tailwind.config.js        # Tailwind CSS configuration
├── postcss.config.js         # PostCSS configuration
├── index.html                # HTML entry point
├── src/
│   ├── main.tsx              # React entry point
│   ├── App.tsx               # Root component
│   ├── App.test.tsx          # App component test
│   ├── index.css             # Global styles with Tailwind
│   ├── vite-env.d.ts         # Vite type declarations
│   └── types/
│       └── index.ts          # Shared TypeScript types
└── vitest.config.ts          # Vitest test configuration
```

---

## Technical Specification

### Data Models

#### DynamoDB Key Patterns
```
Characters: PK=USER#{user_id}, SK=CHAR#{char_id}
Sessions:   PK=USER#{user_id}, SK=SESS#{sess_id}
Messages:   PK=SESS#{sess_id}, SK=MSG#{timestamp}

GSI1: (for reverse lookups)
  GSI1PK, GSI1SK - flexible for future access patterns
```

#### Pydantic Models (`lambdas/shared/models.py`)
```python
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CharacterClass(str, Enum):
    """BECMI character classes."""
    FIGHTER = "fighter"
    THIEF = "thief"
    MAGIC_USER = "magic_user"
    CLERIC = "cleric"


class AbilityScores(BaseModel):
    """D&D ability scores (3-18 range)."""
    strength: int = Field(..., ge=3, le=18)
    intelligence: int = Field(..., ge=3, le=18)
    wisdom: int = Field(..., ge=3, le=18)
    dexterity: int = Field(..., ge=3, le=18)
    constitution: int = Field(..., ge=3, le=18)
    charisma: int = Field(..., ge=3, le=18)


class Item(BaseModel):
    """Inventory item."""
    name: str
    quantity: int = Field(default=1, ge=1)
    weight: float = Field(default=0.0, ge=0)
    description: Optional[str] = None


class Character(BaseModel):
    """Player character model."""
    character_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    name: str = Field(..., min_length=1, max_length=50)
    character_class: CharacterClass
    level: int = Field(default=1, ge=1, le=36)
    xp: int = Field(default=0, ge=0)
    hp: int = Field(default=1, ge=0)
    max_hp: int = Field(default=1, ge=1)
    gold: int = Field(default=0, ge=0)
    abilities: AbilityScores
    inventory: list[Item] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None


class MessageRole(str, Enum):
    """Message sender role."""
    PLAYER = "player"
    DM = "dm"


class Message(BaseModel):
    """Game message in session history."""
    role: MessageRole
    content: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Session(BaseModel):
    """Game session with state."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    character_id: str
    campaign_setting: str = Field(default="default")
    current_location: str = Field(default="Unknown")
    world_state: dict = Field(default_factory=dict)
    message_history: list[Message] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None
```

### API Gateway Configuration
| Property | Value |
|----------|-------|
| Type | REST API |
| Stage | `dev` / `prod` |
| CORS Origins | `chaos.jurigregg.com` (prod), `*` (dev) |
| Throttling | 100 req/s, burst 200 |

### Lambda Configuration
| Property | Value |
|----------|-------|
| Runtime | Python 3.12 |
| Memory | 256 MB |
| Timeout | 30 seconds |
| Tracing | X-Ray enabled |
| Log Level | DEBUG (dev), INFO (prod) |

---

## Implementation Steps

### Step 1: Create CDK Project Structure
**Files**: `cdk/app.py`, `cdk/cdk.json`, `cdk/requirements.txt`

Create the CDK app entry point and configuration.

```python
# cdk/app.py
#!/usr/bin/env python3
"""CDK app entry point for Chaos Dungeon."""
import os

import aws_cdk as cdk

from stacks.base_stack import ChaosBaseStack
from stacks.api_stack import ChaosApiStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

environment = app.node.try_get_context("environment") or "dev"

base_stack = ChaosBaseStack(
    app, f"ChaosBase-{environment}",
    environment=environment,
    env=env,
)

api_stack = ChaosApiStack(
    app, f"ChaosApi-{environment}",
    environment=environment,
    base_stack=base_stack,
    env=env,
)

app.synth()
```

**Validation**:
- [ ] `cdk synth` runs without syntax errors

### Step 2: Create Base Stack (DynamoDB + Secrets + Layer)
**Files**: `cdk/stacks/__init__.py`, `cdk/stacks/base_stack.py`

Create the base infrastructure stack with:
- DynamoDB table with single-table design
- Secrets Manager secret for Claude API key
- Lambda layer for shared Python code

Key implementation details:
- Use `PAY_PER_REQUEST` billing mode
- Add GSI1 for future access patterns
- Layer bundles `shared/` and installs requirements
- Retain table in prod, destroy in dev

**Validation**:
- [ ] `cdk synth` includes DynamoDB table with correct schema
- [ ] GSI1 is present in synthesized template
- [ ] Lambda layer is defined

### Step 3: Create API Stack (API Gateway)
**Files**: `cdk/stacks/api_stack.py`

Create the API Gateway REST API with:
- CORS configuration (restrictive in prod)
- Environment-based stage name
- Throttling configuration
- Placeholder for Lambda integrations (actual handlers in later PRPs)

**Validation**:
- [ ] `cdk synth` includes API Gateway
- [ ] CORS is configured correctly

### Step 4: Create Lambda Shared Module
**Files**: `lambdas/shared/__init__.py`, `lambdas/shared/config.py`, `lambdas/shared/exceptions.py`

Create shared utilities for Lambda functions:
- Environment configuration from env vars
- Custom exception classes for error handling

```python
# lambdas/shared/exceptions.py
"""Custom exceptions for Chaos Dungeon."""


class ChaosDungeonError(Exception):
    """Base exception for all game errors."""
    pass


class NotFoundError(ChaosDungeonError):
    """Resource not found."""
    pass


class ValidationError(ChaosDungeonError):
    """Request validation failed."""
    pass


class GameStateError(ChaosDungeonError):
    """Invalid game state transition."""
    pass
```

**Validation**:
- [ ] Modules can be imported without errors
- [ ] Type hints are present

### Step 5: Create Database Client
**Files**: `lambdas/shared/db.py`

Create DynamoDB client wrapper following the pattern in `examples/lambda/db_pattern.py`:
- Generic CRUD operations
- PK/SK key management
- Error handling with logging
- Type-safe with generics

**Validation**:
- [ ] All methods have type hints
- [ ] Error handling uses custom exceptions

### Step 6: Create Pydantic Models
**Files**: `lambdas/shared/models.py`

Create data models based on `docs/PLANNING.md`:
- Character model with BECMI attributes
- Session model with game state
- Message model for chat history
- Methods for DynamoDB serialization

**Validation**:
- [ ] Models can serialize to/from DynamoDB format
- [ ] Validation constraints match BECMI rules

### Step 7: Create Utility Functions
**Files**: `lambdas/shared/utils.py`

Create common utilities:
- UUID generation
- Timestamp formatting
- User ID extraction from headers
- Response formatting helpers

**Validation**:
- [ ] All functions have docstrings
- [ ] Type hints present

### Step 8: Create Python Project Configuration
**Files**: `lambdas/pyproject.toml`, `lambdas/requirements.txt`, `lambdas/requirements-dev.txt`

Configure Python tooling:
- ruff for linting
- pytest configuration
- Runtime and dev dependencies

```toml
# lambdas/pyproject.toml
[project]
name = "chaos-dungeon-lambdas"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=shared --cov-report=term-missing"
```

**Validation**:
- [ ] `ruff check .` passes
- [ ] pytest can discover tests

### Step 9: Create Python Tests
**Files**: `lambdas/tests/__init__.py`, `lambdas/tests/conftest.py`, `lambdas/tests/test_shared.py`

Create test infrastructure and initial tests:
- pytest fixtures for mocked DynamoDB
- Unit tests for models
- Unit tests for db client
- Unit tests for utilities

**Validation**:
- [ ] `pytest` runs successfully
- [ ] Coverage > 80% for shared module

### Step 10: Create CDK Tests
**Files**: `cdk/tests/__init__.py`, `cdk/tests/test_stacks.py`

Create CDK stack tests:
- Snapshot tests for both stacks
- Assertion tests for critical resources

**Validation**:
- [ ] CDK tests pass

### Step 11: Create Frontend Scaffolding
**Files**: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`

Set up the React + TypeScript + Vite project:
- React 18 with strict mode
- TypeScript with strict settings
- Vite for fast development

**Validation**:
- [ ] `npm install` succeeds
- [ ] TypeScript compiles without errors

### Step 12: Create Tailwind Configuration
**Files**: `frontend/tailwind.config.js`, `frontend/postcss.config.js`

Configure Tailwind CSS v3:
- Dark theme colors (slate, amber)
- Mobile-first breakpoints
- Custom spacing if needed

**Validation**:
- [ ] Tailwind classes work in components

### Step 13: Create React Entry Points
**Files**: `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/src/vite-env.d.ts`

Create the React application shell:
- Basic routing placeholder
- Dark theme styling
- Responsive layout skeleton

**Validation**:
- [ ] `npm run dev` starts server
- [ ] App renders without errors

### Step 14: Create Frontend Types
**Files**: `frontend/src/types/index.ts`

Create shared TypeScript types mirroring backend models:
- Character interface
- Session interface
- Message interface
- API response types

**Validation**:
- [ ] Types match backend models
- [ ] No TypeScript errors

### Step 15: Create Frontend Tests
**Files**: `frontend/vitest.config.ts`, `frontend/src/App.test.tsx`

Set up Vitest for frontend testing:
- React Testing Library integration
- jsdom environment
- Initial App component test

**Validation**:
- [ ] `npm test` runs successfully

---

## Testing Requirements

### Unit Tests

#### Python (`lambdas/tests/`)
- `test_models.py`: Character, Session, Message serialization
- `test_db.py`: DynamoDB client operations (mocked)
- `test_exceptions.py`: Exception hierarchy
- `test_config.py`: Environment configuration
- `test_utils.py`: Utility functions

#### TypeScript (`frontend/src/`)
- `App.test.tsx`: Root component renders

### CDK Tests (`cdk/tests/`)
- Snapshot tests for `ChaosBaseStack`
- Snapshot tests for `ChaosApiStack`
- Assertion: DynamoDB table has correct keys
- Assertion: API Gateway has CORS configured

### Manual Testing
1. Run `cdk synth` and verify CloudFormation output
2. Run `npm run dev` and verify frontend loads
3. Run `pytest` and verify all tests pass
4. Run `npm test` and verify frontend tests pass
5. Run `ruff check .` in lambdas directory

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependencies | Install requirements |
| `ValidationError` | Invalid Pydantic model | Return 400 with details |
| `ClientError` | DynamoDB operation failed | Log and re-raise |
| `NotFoundError` | Resource doesn't exist | Return 404 |

### Edge Cases
- Empty table name in config → raise `ConfigurationError`
- Invalid user ID format → `ValidationError`
- DynamoDB conditional check fails → Handle gracefully
- Missing environment variables → Provide sensible defaults for dev

---

## Cost Impact

### Claude API
- No direct usage in this PRP (foundation only)
- Estimated monthly impact: $0

### AWS
| Resource | Est. Monthly Cost | Notes |
|----------|-------------------|-------|
| DynamoDB | $0-1 | On-demand, minimal in dev |
| Secrets Manager | $0.40 | 1 secret |
| Lambda | $0 | Free tier covers testing |
| API Gateway | $0 | Minimal requests in dev |
| CloudWatch Logs | $0-0.50 | Log retention 1 week |
| **Total** | **~$1** | Development phase |

---

## Open Questions

1. ~~Anonymous sessions vs Cognito auth for MVP?~~ → **Resolved**: ADR-005 states anonymous sessions for MVP
2. Should we set up a separate dev/staging AWS account or use same account with environment prefix?
   - **Recommendation**: Same account with environment prefix for cost simplicity
3. Should Lambda layer be rebuilt on every deploy or cached?
   - **Recommendation**: Use CDK's bundling cache, only rebuild when code changes

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements are well-defined in initial file |
| Feasibility | 10 | Standard AWS patterns, well-documented |
| Completeness | 9 | All foundation components covered |
| Alignment | 10 | Matches PLANNING.md and ADRs exactly |
| **Overall** | **9.5** | High confidence - standard infrastructure |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed (none for this PRP)
- [x] Success criteria are measurable
- [x] File structure matches project conventions
- [x] Code patterns match examples/ folder
