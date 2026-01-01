# init-04-frontend-shell

## Overview

Extend the existing React frontend scaffolding with routing, page components, API service layer, user identity management, and age verification gate. This creates the navigable structure for the game without implementing the actual game UI (covered in init-07).

## Dependencies

- init-01-project-foundation (Frontend scaffolding with Vite, React, Tailwind)
- init-02-character-api (Character endpoints to call)
- init-03-session-api (Session endpoints to call)

## Goals

1. **React Router** - Client-side routing with protected routes
2. **Page Structure** - Home, Characters, New Game, Game (placeholder), 404
3. **API Service** - Typed fetch wrapper for backend calls
4. **User Identity** - Anonymous UUID in localStorage (per ADR-005)
5. **Age Verification** - Gate on first visit (per ADR-007)
6. **Global Context** - User state available throughout app

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | `HomePage` | Landing page with "Start Playing" CTA |
| `/characters` | `CharactersPage` | List characters, create new |
| `/characters/new` | `NewCharacterPage` | Character creation form |
| `/play/:sessionId` | `GamePage` | Game UI (placeholder for init-07) |
| `/sessions/new` | `NewSessionPage` | Select character + campaign to start |
| `*` | `NotFoundPage` | 404 page |

## Components

### Layout Components

**`AppLayout`** - Wraps all pages
```
┌─────────────────────────────────────┐
│  Header (logo, nav links)           │
├─────────────────────────────────────┤
│                                     │
│  {children} - Page content          │
│                                     │
├─────────────────────────────────────┤
│  Footer (minimal - version, links)  │
└─────────────────────────────────────┘
```

**`AgeGate`** - Modal on first visit
- "This game contains mature content. Are you 18 or older?"
- Yes → sets `ageVerified: true` in localStorage
- No → redirects to Google

### Page Components

**`HomePage`**
- Hero section with game title/tagline
- "Start Playing" button → `/characters`
- Brief feature highlights
- Dark fantasy aesthetic

**`CharactersPage`**
- List of user's characters (cards)
- Each card shows: name, class, level
- Click card → select for new session
- "Create New Character" button → `/characters/new`
- Empty state if no characters

**`NewCharacterPage`**
- Name input (3-30 chars)
- Class selection (4 radio buttons with descriptions)
- "Roll Character" button
- Shows rolled stats, HP, gold before confirming
- "Create" submits to API → redirects to `/characters`

**`NewSessionPage`**
- Character selector (dropdown or cards)
- Campaign selector (4 options with descriptions)
- "Begin Adventure" button
- Creates session via API → redirects to `/play/{sessionId}`

**`GamePage`** (placeholder)
- Just shows session ID and "Game UI coming in init-07"
- Will be fully implemented in init-07-game-ui

**`NotFoundPage`**
- "Page not found" message
- Link back to home

## API Service Layer

### Structure
```
frontend/src/
├── services/
│   ├── api.ts           # Base fetch wrapper with error handling
│   ├── characters.ts    # Character API methods
│   └── sessions.ts      # Session API methods
```

### Base API Client (`api.ts`)
```typescript
const API_BASE = import.meta.env.VITE_API_URL || '/api';

interface ApiError {
  error: string;
  details?: Record<string, unknown>;
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const userId = getUserId(); // from localStorage
  
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': userId,
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new ApiRequestError(response.status, error.error, error.details);
  }
  
  if (response.status === 204) return undefined as T;
  return response.json();
}
```

### Character Service (`characters.ts`)
```typescript
export const characterService = {
  list: () => request<CharacterListResponse>('/characters'),
  get: (id: string) => request<Character>(`/characters/${id}`),
  create: (data: CharacterCreateRequest) => 
    request<Character>('/characters', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: CharacterUpdateRequest) =>
    request<Character>(`/characters/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => 
    request<void>(`/characters/${id}`, { method: 'DELETE' }),
};
```

### Session Service (`sessions.ts`)
```typescript
export const sessionService = {
  list: (characterId?: string) => 
    request<SessionListResponse>(`/sessions${characterId ? `?character_id=${characterId}` : ''}`),
  get: (id: string) => request<Session>(`/sessions/${id}`),
  create: (data: SessionCreateRequest) =>
    request<Session>('/sessions', { method: 'POST', body: JSON.stringify(data) }),
  getHistory: (id: string, limit?: number, before?: string) =>
    request<MessageHistoryResponse>(`/sessions/${id}/history?limit=${limit || 20}${before ? `&before=${before}` : ''}`),
  delete: (id: string) =>
    request<void>(`/sessions/${id}`, { method: 'DELETE' }),
};
```

## User Identity Context

### UserContext
```typescript
interface UserContextValue {
  userId: string;
  ageVerified: boolean;
  setAgeVerified: (verified: boolean) => void;
}

// Generate UUID on first visit, persist in localStorage
// Expose via React Context for all components
```

### localStorage Keys
- `chaos_user_id` - UUID v4 for API calls
- `chaos_age_verified` - boolean for age gate

## TypeScript Types

Extend `frontend/src/types/index.ts` with full API types:

```typescript
// Character types
interface Character {
  character_id: string;
  name: string;
  character_class: CharacterClass;
  level: number;
  xp: number;
  hp: number;
  max_hp: number;
  gold: number;
  abilities: AbilityScores;
  inventory: Item[];
  created_at: string;
  updated_at: string | null;
}

interface CharacterSummary {
  character_id: string;
  name: string;
  character_class: CharacterClass;
  level: number;
  created_at: string;
}

// Session types
interface Session {
  session_id: string;
  character_id: string;
  campaign_setting: CampaignSetting;
  current_location: string;
  world_state: Record<string, unknown>;
  message_history: Message[];
  created_at: string;
  updated_at: string | null;
}

interface SessionSummary {
  session_id: string;
  character_id: string;
  character_name: string;
  campaign_setting: CampaignSetting;
  current_location: string;
  created_at: string;
  updated_at: string | null;
}

// Enums
type CharacterClass = 'fighter' | 'thief' | 'magic_user' | 'cleric';
type CampaignSetting = 'default' | 'dark_forest' | 'cursed_castle' | 'forgotten_mines';
type MessageRole = 'player' | 'dm';
```

## Styling Guidelines

Follow dark fantasy aesthetic (per ADR-007):
- **Background**: Slate-900/950 (#0f172a / #020617)
- **Text**: Slate-100/200 for body, Amber-500 for accents
- **Cards**: Slate-800 with subtle borders
- **Buttons**: Amber-600 primary, Slate-700 secondary
- **Fonts**: System fonts, consider medieval/fantasy display font for headers

### Responsive Breakpoints
- Mobile-first approach
- `sm`: 640px (larger phones)
- `md`: 768px (tablets)
- `lg`: 1024px (desktop)

## File Structure

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── index.ts
│   ├── ui/
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Loading.tsx
│   │   └── index.ts
│   └── AgeGate.tsx
├── pages/
│   ├── HomePage.tsx
│   ├── CharactersPage.tsx
│   ├── NewCharacterPage.tsx
│   ├── NewSessionPage.tsx
│   ├── GamePage.tsx
│   ├── NotFoundPage.tsx
│   └── index.ts
├── context/
│   ├── UserContext.tsx
│   └── index.ts
├── services/
│   ├── api.ts
│   ├── characters.ts
│   ├── sessions.ts
│   └── index.ts
├── hooks/
│   ├── useLocalStorage.ts
│   └── index.ts
├── types/
│   └── index.ts
├── App.tsx
├── main.tsx
└── index.css
```

## Dependencies to Add

```json
{
  "dependencies": {
    "react-router-dom": "^6.22.0"
  }
}
```

## Environment Variables

```env
# .env.development
VITE_API_URL=http://localhost:3001/api

# .env.production
VITE_API_URL=https://api.chaos.jurigregg.com
```

## Acceptance Criteria

### Routing
- [ ] All routes render correct components
- [ ] 404 page shows for unknown routes
- [ ] Browser back/forward navigation works

### Age Gate
- [ ] Modal appears on first visit
- [ ] "Yes" stores verification and dismisses modal
- [ ] "No" redirects away from site
- [ ] Subsequent visits skip age gate

### User Identity
- [ ] UUID generated on first visit
- [ ] UUID persists across page refreshes
- [ ] UUID included in all API requests

### API Integration
- [ ] Character list loads from API
- [ ] Character creation works end-to-end
- [ ] Session creation works end-to-end
- [ ] Error states displayed to user

### Pages
- [ ] Home page renders with CTA
- [ ] Characters page lists user's characters
- [ ] New character form validates input
- [ ] New session page shows character/campaign selection
- [ ] Game page displays session ID (placeholder)

### Responsive Design
- [ ] All pages usable on mobile (375px+)
- [ ] Layout adjusts for tablet/desktop
- [ ] Touch targets are 44px+ on mobile

### Tests
- [ ] Component unit tests for pages
- [ ] API service tests (mocked fetch)
- [ ] Context tests for user state
- [ ] >70% frontend test coverage

## Implementation Notes

1. **React Router v6** - Use `createBrowserRouter` with `RouterProvider`
2. **Error Boundaries** - Wrap routes in error boundary for graceful failures
3. **Loading States** - Show skeleton/spinner while fetching data
4. **Optimistic UI** - Consider for character deletion
5. **Form Validation** - Client-side validation before API calls

## Out of Scope (Future Init Files)

- Game chat UI (init-07)
- Character sheet view (init-15)
- Session resume flow (init-14)
- Dice rolling animations (init-11)
