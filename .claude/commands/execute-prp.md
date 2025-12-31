# Execute PRP

Execute a Project Requirement Plan step by step with validation.

## Arguments
- `$ARGUMENTS` - Path to the PRP file (e.g., `prps/prp-character-api.md`)

## Instructions

You are executing a PRP (Project Requirement Plan) for the Chaos Dungeon project.

### Step 1: Load and Validate PRP

1. Read the PRP file at `$ARGUMENTS`
2. Verify all sections are complete:
   - Overview and Success Criteria defined
   - Implementation Steps are clear and ordered
   - Testing Requirements specified
3. Read `docs/TASK.md` and check if this work is tracked
4. If not tracked in TASK.md, add it now

### Step 2: Pre-Flight Checks

Before starting implementation:
1. Verify dependencies exist (files to modify, modules to import)
2. Check that referenced examples in `examples/` exist
3. Confirm no conflicting work in progress
4. Run existing tests to ensure clean baseline:
   - `cd lambdas && pytest -q` (if Lambda code exists)
   - `cd frontend && npm test` (if frontend exists)
   - `cd cdk && pytest -q` (if CDK tests exist)

### Step 3: Execute Implementation Steps

For each step in the PRP:
1. Announce which step you're starting
2. Implement the change following project patterns from `CLAUDE.md`:
   - Use Powertools for Lambda
   - Use Pydantic for validation
   - Keep files under 500 lines
   - Follow naming conventions
3. After completing the step, validate:
   - Code compiles/parses without errors
   - Imports resolve correctly
   - No obvious logic errors
4. Mark step as complete before moving to next

### Step 4: Testing

After all implementation steps complete:

1. **Run Linters**
   ```bash
   cd lambdas && ruff check . --fix
   cd cdk && ruff check . --fix
   cd frontend && npm run lint -- --fix
   ```

2. **Run Tests**
   ```bash
   cd lambdas && pytest --tb=short
   cd frontend && npm test -- --passWithNoTests
   cd cdk && pytest --tb=short
   ```

3. **Verify CDK Synth** (if CDK changes)
   ```bash
   cd cdk && cdk synth
   ```

4. If tests fail:
   - Analyze the failure
   - Fix the issue
   - Re-run tests
   - Continue until all pass

### Step 5: Update Documentation

1. Update `docs/TASK.md`:
   - Mark relevant tasks as complete
   - Add any new tasks discovered
2. If architecture decisions were made, add to `docs/DECISIONS.md`
3. Update `README.md` if user-facing changes

### Step 6: Commit and Push

Create a commit following conventional commit format:
```bash
git add .
git commit -m "feat: <description based on PRP title>

Implements PRP: $ARGUMENTS

- <key change 1>
- <key change 2>
- <key change 3>"
git push
```

### Step 7: Completion Report

Report on execution:
1. Summary of what was implemented
2. Files created/modified (list with paths)
3. Test results
4. Any deviations from the PRP (and why)
5. Suggested follow-up tasks (if any)
6. Cost impact notes (if applicable)

## Error Handling

If execution fails at any step:
1. Stop and report the failure
2. Show the error message
3. Suggest potential fixes
4. Ask if user wants to:
   - Retry the step
   - Skip and continue
   - Abort execution

## Budget Check

After completion, if the feature impacts Claude API usage:
1. Estimate tokens per request
2. Calculate monthly cost impact
3. Verify still within $20/month budget
4. Flag if approaching budget limit

## Example Usage

```
/execute-prp prps/prp-character-api.md
```

This would:
1. Load and validate the PRP
2. Execute each implementation step
3. Run all tests and linters
4. Update TASK.md
5. Commit with proper message
6. Push to remote
7. Report completion status
