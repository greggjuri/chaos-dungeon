# PRP-13: Version Display

**Created**: 2026-01-08
**Initial**: `initials/init-13-version-display.md`
**Status**: Ready

---

## Overview

### Problem Statement
After deploying updates to production, there's no easy way to verify the correct version is live. This leads to uncertainty during deploys and debugging.

### Proposed Solution
Display the app version from `package.json` in a small, unobtrusive footer element visible on all pages. The version is read at build time using Vite's `define` configuration.

### Success Criteria
- [ ] Version number displayed in bottom-right corner (e.g., "v0.12.0")
- [ ] Visible on all pages without interfering with UI
- [ ] Version updates automatically from `package.json` at build time
- [ ] No runtime cost (version baked into bundle)

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Frontend uses React + Vite + Tailwind
- No relevant ADRs - this is a simple UI addition

### Dependencies
- Required: None
- Optional: None

### Files to Modify/Create
```
frontend/package.json           # Update version to 0.12.0
frontend/vite.config.ts         # Add define for APP_VERSION
frontend/src/vite-env.d.ts      # TypeScript declaration for APP_VERSION
frontend/src/components/ui/Version.tsx      # New component
frontend/src/components/ui/index.ts         # Export Version
frontend/src/App.tsx            # Add Version component
```

---

## Technical Specification

### Vite Configuration
```typescript
// vite.config.ts
import pkg from './package.json';

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  // ...existing config
});
```

### TypeScript Declaration
```typescript
// vite-env.d.ts (add to existing)
declare const __APP_VERSION__: string;
```

### Component Structure
```tsx
// Version.tsx
export function Version() {
  return (
    <div className="fixed bottom-2 right-2 text-gray-600 text-xs z-40">
      v{__APP_VERSION__}
    </div>
  );
}
```

---

## Implementation Steps

### Step 1: Update package.json version
**Files**: `frontend/package.json`

Change version from `0.1.0` to `0.12.0` to match init number.

```json
{
  "version": "0.12.0"
}
```

**Validation**:
- [ ] Version number is valid semver

### Step 2: Configure Vite to expose version
**Files**: `frontend/vite.config.ts`

Add `define` option to inject version at build time.

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import pkg from './package.json';

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  // ...rest of config
});
```

**Validation**:
- [ ] `npm run build` succeeds
- [ ] Version appears in built bundle

### Step 3: Add TypeScript declaration
**Files**: `frontend/src/vite-env.d.ts`

Add type declaration for the global constant.

```typescript
declare const __APP_VERSION__: string;
```

**Validation**:
- [ ] No TypeScript errors

### Step 4: Create Version component
**Files**: `frontend/src/components/ui/Version.tsx`

Simple component displaying version in bottom-right corner.

```tsx
/**
 * Version display component.
 * Shows app version in bottom-right corner.
 */
export function Version() {
  return (
    <div className="fixed bottom-2 right-2 text-gray-600 text-xs z-40 pointer-events-none select-none">
      v{__APP_VERSION__}
    </div>
  );
}
```

**Validation**:
- [ ] Component renders without errors
- [ ] Positioned correctly (bottom-right, below TokenCounter)

### Step 5: Export from ui/index.ts
**Files**: `frontend/src/components/ui/index.ts`

Add export for Version component.

**Validation**:
- [ ] Import works from `../components`

### Step 6: Add to App.tsx
**Files**: `frontend/src/App.tsx`

Render Version component at app root so it appears on all pages.

**Validation**:
- [ ] Version visible on home page
- [ ] Version visible on game page
- [ ] Version visible on character creation

---

## Testing Requirements

### Unit Tests
- Not required for this simple display component

### Manual Testing
1. Run `npm run dev` and verify version shows on all pages
2. Run `npm run build && npm run preview` and verify version in production build
3. Verify version doesn't overlap with TokenCounter (when visible)

---

## Integration Test Plan

### Prerequisites
- Frontend running: `cd frontend && npm run dev`

### Test Steps
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Open home page | "v0.12.0" visible in bottom-right | ☐ |
| 2 | Navigate to character creation | Version still visible | ☐ |
| 3 | Start a game session | Version visible on game page | ☐ |
| 4 | Press 'T' to show TokenCounter | Both elements visible, no overlap | ☐ |
| 5 | Build for production | Version in bundle, displays correctly | ☐ |

### Browser Checks
- [ ] No JavaScript errors in Console
- [ ] Version text is readable but unobtrusive (gray-600)
- [ ] Position is fixed and doesn't scroll with content

---

## Error Handling

### Expected Errors
None - this is a static display component.

### Edge Cases
- TokenCounter visible: Version should be below it (bottom-2 vs bottom-16)
- Very narrow mobile screens: Text might be partially hidden - acceptable

---

## Cost Impact

### Claude API
- None - no AI involvement

### AWS
- Negligible bundle size increase (~50 bytes)
- No new resources

---

## Open Questions

None - straightforward implementation.

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Very simple, well-defined scope |
| Feasibility | 10 | Standard Vite pattern, no blockers |
| Completeness | 10 | All aspects covered |
| Alignment | 10 | Helps with deployment verification |
| **Overall** | **10** | Trivial feature, 15-minute implementation |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive (N/A for this feature)
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
