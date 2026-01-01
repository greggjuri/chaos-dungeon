# PRP-04: Frontend Shell

**Created**: 2026-01-01
**Initial**: `initials/init-04-frontend-shell.md`
**Status**: Ready

---

## Overview

### Problem Statement
The frontend currently has only a placeholder App.tsx with no routing, pages, or API integration. Users cannot navigate to different views, create characters, or start game sessions through the UI.

### Proposed Solution
Build a complete React frontend shell with:
- React Router v6 for client-side navigation
- Page components for all major routes (Home, Characters, New Character, New Session, Game, 404)
- API service layer with typed fetch wrapper
- User identity context (anonymous UUID per ADR-005)
- Age verification gate (per ADR-007)
- Reusable UI components (Button, Card, Input, Select, Loading)
- Dark fantasy styling consistent with existing theme

### Success Criteria
- [ ] All 6 routes render correct components with browser navigation
- [ ] Age gate modal appears on first visit, persists verification
- [ ] UUID generated and included in all API requests
- [ ] Character list/creation works end-to-end with backend
- [ ] Session creation works end-to-end with backend
- [ ] All pages responsive on mobile (375px+)
- [ ] >70% frontend test coverage
- [ ] ESLint/TypeScript pass with 0 errors

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Frontend tech stack (React 18 + TypeScript + Tailwind)
- `docs/DECISIONS.md` - ADR-005 (Anonymous Sessions), ADR-007 (Mature Content), ADR-008 (React + Vite)
- React Router v6 docs: https://reactrouter.com/

### Dependencies
- **Required**:
  - init-01-project-foundation (Frontend scaffolding) ✅
  - init-02-character-api (Character endpoints) ✅
  - init-03-session-api (Session endpoints) ✅
- **Optional**: None

### Files to Modify/Create
```
frontend/src/
├── App.tsx                      # Replace with RouterProvider setup
├── types/index.ts               # Add API response types
├── context/
│   ├── UserContext.tsx          # User identity + age verification
│   └── index.ts
├── services/
│   ├── api.ts                   # Base fetch wrapper
│   ├── characters.ts            # Character API service
│   ├── sessions.ts              # Session API service
│   └── index.ts
├── hooks/
│   ├── useLocalStorage.ts       # localStorage hook
│   └── index.ts
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx        # Main layout wrapper
│   │   ├── Header.tsx           # Navigation header
│   │   ├── Footer.tsx           # Page footer
│   │   └── index.ts
│   ├── ui/
│   │   ├── Button.tsx           # Styled button
│   │   ├── Card.tsx             # Content card
│   │   ├── Input.tsx            # Form input
│   │   ├── Select.tsx           # Form select
│   │   ├── Loading.tsx          # Loading spinner
│   │   └── index.ts
│   ├── AgeGate.tsx              # Age verification modal
│   └── index.ts
├── pages/
│   ├── HomePage.tsx             # Landing page
│   ├── CharactersPage.tsx       # Character list
│   ├── NewCharacterPage.tsx     # Character creation form
│   ├── NewSessionPage.tsx       # Start new game
│   ├── GamePage.tsx             # Game placeholder
│   ├── NotFoundPage.tsx         # 404 page
│   └── index.ts
```

---

## Technical Specification

### TypeScript Types (additions to types/index.ts)

```typescript
// API Response types
export interface CharacterListResponse {
  characters: CharacterSummary[];
}

export interface CharacterSummary {
  character_id: string;
  name: string;
  character_class: CharacterClass;
  level: number;
  created_at: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
}

export interface SessionSummary {
  session_id: string;
  character_id: string;
  character_name: string;
  campaign_setting: CampaignSetting;
  current_location: string;
  created_at: string;
  updated_at: string | null;
}

export type CampaignSetting = 'default' | 'dark_forest' | 'cursed_castle' | 'forgotten_mines';

export interface MessageHistoryResponse {
  messages: Message[];
  has_more: boolean;
  next_cursor: string | null;
}

export interface SessionCreateRequest {
  character_id: string;
  campaign_setting?: CampaignSetting;
}

export interface SessionCreateResponse {
  session_id: string;
  character_id: string;
  campaign_setting: CampaignSetting;
  current_location: string;
  world_state: Record<string, unknown>;
  message_history: Message[];
  created_at: string;
}

// Error types
export interface ApiError {
  error: string;
  details?: Record<string, unknown>;
}

export class ApiRequestError extends Error {
  constructor(
    public status: number,
    public error: string,
    public details?: Record<string, unknown>
  ) {
    super(error);
    this.name = 'ApiRequestError';
  }
}
```

### Routes Configuration

| Path | Component | Protected | Description |
|------|-----------|-----------|-------------|
| `/` | `HomePage` | No | Landing page |
| `/characters` | `CharactersPage` | Yes* | List characters |
| `/characters/new` | `NewCharacterPage` | Yes* | Create character |
| `/sessions/new` | `NewSessionPage` | Yes* | Start new game |
| `/play/:sessionId` | `GamePage` | Yes* | Game UI placeholder |
| `*` | `NotFoundPage` | No | 404 page |

*Protected = requires age verification

### User Context

```typescript
interface UserContextValue {
  userId: string;
  ageVerified: boolean;
  setAgeVerified: (verified: boolean) => void;
}
```

**localStorage Keys:**
- `chaos_user_id` - UUID v4 string
- `chaos_age_verified` - "true" or not present

---

## Implementation Steps

### Step 1: Add Dependencies
**Files**: `frontend/package.json`

Install react-router-dom for client-side routing.

```bash
cd frontend && npm install react-router-dom
```

**Validation**:
- [ ] Package installed successfully
- [ ] No TypeScript errors

---

### Step 2: Create Utility Hook
**Files**: `frontend/src/hooks/useLocalStorage.ts`, `frontend/src/hooks/index.ts`

Create a type-safe localStorage hook for persisting user state.

```typescript
// useLocalStorage.ts
import { useState, useCallback } from 'react';

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const valueToStore = value instanceof Function ? value(prev) : value;
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
        return valueToStore;
      });
    },
    [key]
  );

  return [storedValue, setValue];
}
```

**Validation**:
- [ ] Hook exports correctly
- [ ] TypeScript compiles

---

### Step 3: Create User Context
**Files**: `frontend/src/context/UserContext.tsx`, `frontend/src/context/index.ts`

Implement user identity with UUID generation and age verification state.

```typescript
// UserContext.tsx
import { createContext, useContext, useMemo, ReactNode } from 'react';
import { useLocalStorage } from '../hooks';

function generateUserId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

interface UserContextValue {
  userId: string;
  ageVerified: boolean;
  setAgeVerified: (verified: boolean) => void;
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId] = useLocalStorage<string>('chaos_user_id', generateUserId());
  const [ageVerified, setAgeVerified] = useLocalStorage<boolean>('chaos_age_verified', false);

  const value = useMemo(
    () => ({ userId, ageVerified, setAgeVerified }),
    [userId, ageVerified, setAgeVerified]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
}
```

**Validation**:
- [ ] Context provides userId, ageVerified, setAgeVerified
- [ ] UUID persists across refreshes

---

### Step 4: Create API Service Layer
**Files**: `frontend/src/services/api.ts`, `frontend/src/services/characters.ts`, `frontend/src/services/sessions.ts`, `frontend/src/services/index.ts`

Build typed API client with error handling.

```typescript
// api.ts
import { ApiRequestError } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export function getUserId(): string {
  const stored = localStorage.getItem('chaos_user_id');
  if (stored) {
    return JSON.parse(stored);
  }
  throw new Error('User ID not found');
}

export async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const userId = getUserId();

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': userId,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new ApiRequestError(response.status, error.error, error.details);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
```

```typescript
// characters.ts
import { request } from './api';
import {
  Character,
  CharacterListResponse,
  CreateCharacterRequest
} from '../types';

export const characterService = {
  list: () => request<CharacterListResponse>('/characters'),

  get: (id: string) => request<Character>(`/characters/${id}`),

  create: (data: CreateCharacterRequest) =>
    request<Character>('/characters', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/characters/${id}`, { method: 'DELETE' }),
};
```

```typescript
// sessions.ts
import { request } from './api';
import {
  SessionListResponse,
  Session,
  SessionCreateRequest,
  SessionCreateResponse,
  MessageHistoryResponse,
} from '../types';

export const sessionService = {
  list: (characterId?: string) => {
    const query = characterId ? `?character_id=${characterId}` : '';
    return request<SessionListResponse>(`/sessions${query}`);
  },

  get: (id: string) => request<Session>(`/sessions/${id}`),

  create: (data: SessionCreateRequest) =>
    request<SessionCreateResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getHistory: (id: string, limit = 20, before?: string) => {
    let query = `?limit=${limit}`;
    if (before) query += `&before=${before}`;
    return request<MessageHistoryResponse>(`/sessions/${id}/history${query}`);
  },

  delete: (id: string) =>
    request<void>(`/sessions/${id}`, { method: 'DELETE' }),
};
```

**Validation**:
- [ ] Services export all methods
- [ ] Types match backend responses

---

### Step 5: Create UI Components
**Files**: `frontend/src/components/ui/*.tsx`

Build reusable UI components following dark fantasy theme.

**Button.tsx** - Primary/secondary variants, loading state
**Card.tsx** - Content container with hover effects
**Input.tsx** - Text input with label and error state
**Select.tsx** - Dropdown with options
**Loading.tsx** - Spinner with optional message

Key styling:
- Primary button: `bg-amber-600 hover:bg-amber-700`
- Secondary button: `bg-slate-700 hover:bg-slate-600`
- Cards: `bg-slate-800 border-slate-700`
- Inputs: `bg-slate-900 border-slate-600 focus:border-amber-500`

**Validation**:
- [ ] All components render correctly
- [ ] Components are accessible (proper aria labels, focus states)

---

### Step 6: Create Layout Components
**Files**: `frontend/src/components/layout/*.tsx`

Build app layout with header, footer, and content area.

**AppLayout.tsx** - Wraps all pages with consistent structure
```tsx
<div className="min-h-screen flex flex-col bg-slate-950">
  <Header />
  <main className="flex-1 container mx-auto px-4 py-8">
    {children}
  </main>
  <Footer />
</div>
```

**Header.tsx** - Logo and navigation links
- Logo: "Chaos Dungeon" with link to home
- Nav links: Characters, New Game (visible when age verified)

**Footer.tsx** - Minimal footer with credits

**Validation**:
- [ ] Layout renders with header/footer
- [ ] Navigation links work

---

### Step 7: Create Age Gate Component
**Files**: `frontend/src/components/AgeGate.tsx`

Modal that appears on first visit for age verification.

```tsx
// AgeGate.tsx
export function AgeGate() {
  const { ageVerified, setAgeVerified } = useUser();

  if (ageVerified) return null;

  const handleYes = () => setAgeVerified(true);
  const handleNo = () => window.location.href = 'https://google.com';

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <Card className="max-w-md text-center">
        <h2>Age Verification</h2>
        <p>This game contains mature content including violence and dark themes.</p>
        <p className="font-bold">Are you 18 years or older?</p>
        <div className="flex gap-4 justify-center">
          <Button onClick={handleYes}>Yes, I am 18+</Button>
          <Button variant="secondary" onClick={handleNo}>No</Button>
        </div>
      </Card>
    </div>
  );
}
```

**Validation**:
- [ ] Modal appears on first visit
- [ ] "Yes" stores verification and dismisses
- [ ] "No" redirects away
- [ ] Subsequent visits skip modal

---

### Step 8: Create Page Components
**Files**: `frontend/src/pages/*.tsx`

Implement all page components:

**HomePage.tsx**
- Hero section with game title and tagline
- "Start Playing" CTA button → `/characters`
- Feature highlights (3-4 key features)
- Dark fantasy aesthetic

**CharactersPage.tsx**
- Fetch and display character list
- Character cards showing name, class, level
- "Create New Character" button
- Empty state when no characters
- Delete character with confirmation

**NewCharacterPage.tsx**
- Name input (validated 3-30 chars)
- Class selection (4 radio buttons with descriptions)
- Submit creates character via API
- Redirect to `/characters` on success

**NewSessionPage.tsx**
- Character selector (dropdown of user's characters)
- Campaign setting selector (4 options with descriptions)
- "Begin Adventure" button
- Creates session via API → redirects to `/play/{sessionId}`

**GamePage.tsx** (placeholder)
- Display session ID from URL params
- "Game UI coming in init-07" message
- Link back to characters

**NotFoundPage.tsx**
- "Page not found" message
- Link back to home

**Validation**:
- [ ] All pages render without errors
- [ ] Forms submit correctly
- [ ] API errors displayed to user

---

### Step 9: Set Up Router and App Entry
**Files**: `frontend/src/App.tsx`

Replace current App with React Router setup:

```tsx
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import { UserProvider } from './context';
import { AppLayout, AgeGate } from './components';
import {
  HomePage,
  CharactersPage,
  NewCharacterPage,
  NewSessionPage,
  GamePage,
  NotFoundPage
} from './pages';

function RootLayout() {
  return (
    <UserProvider>
      <AgeGate />
      <AppLayout>
        <Outlet />
      </AppLayout>
    </UserProvider>
  );
}

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/characters', element: <CharactersPage /> },
      { path: '/characters/new', element: <NewCharacterPage /> },
      { path: '/sessions/new', element: <NewSessionPage /> },
      { path: '/play/:sessionId', element: <GamePage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
```

**Validation**:
- [ ] All routes accessible
- [ ] Browser navigation works
- [ ] 404 shows for unknown routes

---

### Step 10: Update Types and Add Environment
**Files**: `frontend/src/types/index.ts`, `frontend/.env.development`, `frontend/.env.production`

Add missing types and environment configuration.

```env
# .env.development
VITE_API_URL=http://localhost:3001/dev

# .env.production
VITE_API_URL=https://api.chaos.jurigregg.com
```

**Validation**:
- [ ] All types compile
- [ ] Environment variables load correctly

---

### Step 11: Write Tests
**Files**: `frontend/src/**/*.test.tsx`

Create tests for:

1. **Component tests** - Each UI component renders correctly
2. **Page tests** - Pages render with mocked data
3. **Service tests** - API calls mocked with correct headers
4. **Context tests** - User state manages correctly
5. **Integration tests** - Navigation flow works

Target: >70% coverage

**Validation**:
- [ ] All tests pass
- [ ] Coverage > 70%

---

### Step 12: Lint and Final Validation
**Files**: All frontend files

Run linters and verify everything works:

```bash
cd frontend
npm run lint
npm run build
npm test -- --coverage
```

**Validation**:
- [ ] ESLint passes with 0 warnings
- [ ] TypeScript compiles
- [ ] Build succeeds
- [ ] Tests pass with >70% coverage

---

## Testing Requirements

### Unit Tests
- Button renders with correct variant styling
- Card renders children correctly
- Input shows error state when provided
- Loading shows spinner and message
- useLocalStorage persists values

### Component Tests
- AgeGate modal appears when not verified
- AgeGate dismisses on "Yes" click
- Header shows nav links when verified
- CharactersPage shows empty state with no characters
- CharactersPage renders character cards
- NewCharacterPage validates form input
- NewSessionPage shows character dropdown

### Service Tests
- API client includes X-User-Id header
- API client throws ApiRequestError on 4xx/5xx
- characterService.list calls correct endpoint
- sessionService.create sends correct body

### Integration Tests
- Full character creation flow (navigate → fill form → submit → redirect)
- Full session creation flow

### Manual Testing
1. Open app fresh (cleared localStorage) → age gate appears
2. Click "Yes" → gate dismisses, navigate to `/characters`
3. Click "Create New Character" → form appears
4. Fill form and submit → redirected to characters list
5. Click character → can start new session
6. Select campaign and start → redirected to game page
7. Browser back/forward works correctly
8. Test on mobile viewport (375px)

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| 401 Unauthorized | Missing X-User-Id | Show error, suggest refresh |
| 404 Not Found | Resource doesn't exist | Show "not found" message |
| 400 Bad Request | Invalid form data | Show validation errors |
| 409 Conflict | Session limit reached | Show limit message |
| Network Error | API unreachable | Show connection error |

### Edge Cases
- User clears localStorage → new UUID generated, age gate reappears
- API returns slow → show loading states
- Character deleted while viewing → handle gracefully
- Invalid session ID in URL → show not found

---

## Cost Impact

### Claude API
- No impact (no AI features in this init)

### AWS
- No new resources
- Minimal S3/CloudFront usage for static files
- Estimated impact: < $0.50/month

---

## Open Questions

1. **None** - Requirements are well-defined in init-04

---

## Confidence Score

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Init spec is detailed with routes, components, types |
| Feasibility | 10 | Standard React patterns, existing foundation |
| Completeness | 9 | All pages, services, tests defined |
| Alignment | 10 | Follows ADRs, uses Tailwind, mobile-first |
| **Overall** | **9.5** | High confidence - clear scope, standard implementation |

---

## Checklist

- [x] All implementation steps are atomic and clear
- [x] Testing requirements are specific
- [x] Error handling is comprehensive
- [x] Cost impact is estimated
- [x] Dependencies are listed
- [x] Success criteria are measurable
