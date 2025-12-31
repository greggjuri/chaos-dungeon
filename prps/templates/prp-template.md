# PRP Template

## PRP-XXX: {Feature Name}

**Created**: YYYY-MM-DD  
**Initial**: `initials/init-{feature}.md`  
**Status**: Draft/Ready/In Progress/Complete

---

## Overview

### Problem Statement
What problem are we solving? Why does this feature matter?

### Proposed Solution
High-level description of what we're building.

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview
- `docs/DECISIONS.md` - Relevant ADRs
- External docs: [links]

### Dependencies
- Required: List features/PRPs that must be complete first
- Optional: Features that enhance but aren't required

### Files to Modify/Create
```
path/to/file1.py    # Description of changes
path/to/file2.tsx   # Description of changes
path/to/new-file.py # New file purpose
```

---

## Technical Specification

### Data Models
```python
# Pydantic models or TypeScript interfaces
class Model(BaseModel):
    field: str
```

### API Changes
| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | /endpoint | `{...}` | `{...}` |

### Component Structure
```
ComponentName/
├── index.tsx
├── ComponentName.tsx
└── ComponentName.test.tsx
```

---

## Implementation Steps

### Step 1: {First Step Title}
**Files**: `path/to/file.py`

Detailed description of what to implement.

```python
# Code example if helpful
```

**Validation**:
- [ ] Tests pass
- [ ] Lint passes

### Step 2: {Second Step Title}
...

### Step 3: {Third Step Title}
...

---

## Testing Requirements

### Unit Tests
- Test case 1: Description
- Test case 2: Description

### Integration Tests
- Test scenario 1: Description

### Manual Testing
1. Step to manually verify
2. Expected result

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| NotFoundError | Resource doesn't exist | Return 404 |

### Edge Cases
- Edge case 1: How to handle
- Edge case 2: How to handle

---

## Cost Impact

### Claude API
- Estimated tokens per request: X
- Estimated monthly impact: $X

### AWS
- New resources: List any new resources
- Estimated monthly impact: $X

---

## Open Questions

1. Question that needs resolution?
2. Uncertainty to clarify?

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | X | How well-defined is scope? |
| Feasibility | X | Can this be built with current architecture? |
| Completeness | X | Does PRP cover all aspects? |
| Alignment | X | Does it align with project goals/budget? |
| **Overall** | X | Average of above |

---

## Checklist

- [ ] All implementation steps are atomic and clear
- [ ] Testing requirements are specific
- [ ] Error handling is comprehensive
- [ ] Cost impact is estimated
- [ ] Dependencies are listed
- [ ] Success criteria are measurable
