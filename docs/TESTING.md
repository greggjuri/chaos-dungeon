# Chaos Dungeon - Testing Standards

## Testing Pyramid

```
        /\
       /  \     Manual/E2E (few)
      /----\
     /      \   Integration (some)
    /--------\
   /          \ Unit (many)
  --------------
```

## When to Test What

| Test Type | When | Tools |
|-----------|------|-------|
| Unit | Every code change | pytest, vitest |
| Integration | After deployment | Browser DevTools |
| E2E | Before releases | Manual checklist |

## Automated Tests (CI)

```bash
# Backend
cd lambdas && pytest --cov=. --cov-report=term-missing

# Frontend
cd frontend && npm test -- --coverage

# CDK
cd cdk && pytest
```

**Minimum Coverage**: 80%

## Manual Integration Testing

Required after every PRP execution that touches:
- API endpoints
- Frontend API calls
- Authentication/headers
- localStorage/state management

### Setup
1. Deploy backend: `cd cdk && cdk deploy --all`
2. Start frontend: `cd frontend && npm run dev`
3. Open DevTools (F12)

### Checklist
- [ ] Console tab: No red errors
- [ ] Network tab: Requests succeed (2xx)
- [ ] Feature works end-to-end
- [ ] Error states handled gracefully

### Common Bugs to Catch

| Bug | How to Detect | Fix Pattern |
|-----|---------------|-------------|
| CORS | Console shows CORS error | Add CORSConfig to Lambda handler |
| Missing header | 401 response | Check X-User-Id in request headers |
| URL malformed | 404 response | Check VITE_API_URL (no trailing slash) |
| State not persisting | localStorage is null | Ensure hook writes initial value |
| JS error blocking action | Nothing in Network tab | Check Console for errors |

## Bug Report Template

```markdown
### Bug
[Brief description]

### Environment
- Browser:
- URL:

### Steps to Reproduce
1.
2.
3.

### Expected
[What should happen]

### Actual
[What actually happened]

### Console Output
[Paste errors]

### Network Tab
[Request/response details]
```

---

## Lessons Learned

### init-04 (Frontend Shell)

| Bug | Root Cause | Prevention |
|-----|------------|------------|
| CORS error | Lambda handler missing CORSConfig | Add to code review checklist |
| useLocalStorage not persisting | Initial value not written to localStorage | Test localStorage in browser |
| Double slash URL | Trailing slash in env + leading slash in code | Validate URL construction |

These bugs passed automated tests but failed in real browser environment. Manual integration testing catches these.
