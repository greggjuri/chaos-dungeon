# init-01: Project Foundation

## Feature Overview

Set up the base project infrastructure including AWS CDK stacks, DynamoDB tables, Lambda layer for shared code, and project scaffolding.

## Requirements

### CDK Infrastructure
1. **Base Stack** (`ChaosBaseStack`):
   - DynamoDB table with single-table design
   - Lambda layer for shared Python code
   - Secrets Manager secret for Claude API key
   - IAM roles with least privilege

2. **API Stack** (`ChaosApiStack`):
   - API Gateway REST API
   - CORS configuration for chaos.jurigregg.com
   - Stage configuration (dev/prod)

### DynamoDB Table Design
- Table Name: `chaos-dungeon-{env}`
- Partition Key: `PK` (String)
- Sort Key: `SK` (String)
- GSI: `GSI1` for reverse lookups if needed
- Billing: PAY_PER_REQUEST (on-demand)

### Key Patterns
```
Characters: PK=USER#{user_id}, SK=CHAR#{char_id}
Sessions:   PK=USER#{user_id}, SK=SESS#{sess_id}
Messages:   PK=SESS#{sess_id}, SK=MSG#{timestamp}
```

### Lambda Layer Contents
```
shared/
├── __init__.py
├── models.py         # Pydantic models
├── db.py             # DynamoDB helpers
├── exceptions.py     # Custom exceptions
├── config.py         # Environment config
└── utils.py          # Utility functions
```

### Project Structure to Create
```
chaos-dungeon/
├── cdk/
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   ├── stacks/
│   │   ├── __init__.py
│   │   ├── base_stack.py
│   │   └── api_stack.py
│   └── tests/
│       └── test_stacks.py
├── lambdas/
│   ├── requirements.txt
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── exceptions.py
│   │   ├── config.py
│   │   └── utils.py
│   └── tests/
│       └── __init__.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── vite-env.d.ts
│   └── tailwind.config.js
└── examples/
    └── README.md
```

## Technical Constraints

### Budget
- DynamoDB on-demand only (no provisioned capacity)
- Single table to minimize costs
- No NAT Gateway (Lambda in public subnets)

### Security
- Claude API key in Secrets Manager
- IAM roles with minimal permissions
- No hardcoded credentials

### Code Quality
- All Python code uses type hints
- Pydantic for all data validation
- AWS Lambda Powertools for logging/tracing
- ruff for linting

## Success Criteria

- [ ] `cdk synth` succeeds without errors
- [ ] DynamoDB table created with correct schema
- [ ] Lambda layer builds successfully
- [ ] Shared models can be imported in Lambda handlers
- [ ] Frontend dev server runs with `npm run dev`
- [ ] All tests pass
- [ ] Total file count per file stays under 500 lines

## Examples to Reference

None yet - this is the foundation.

## Documentation Links

- [AWS CDK Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
- [DynamoDB Single Table](https://www.alexdebrie.com/posts/dynamodb-single-table/)
- [Lambda Powertools](https://docs.powertools.aws.dev/lambda/python/latest/)
- [Pydantic V2](https://docs.pydantic.dev/latest/)

## Other Considerations

1. Use Python 3.12 runtime for Lambda
2. Frontend uses React 18 with strict mode
3. Tailwind CSS v3 for styling
4. Environment-based configuration (dev/prod)
5. Git ignore patterns for node_modules, __pycache__, .cdk.out
