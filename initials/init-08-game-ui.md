# init-08-game-ui

## Overview

Implement the game chat interface where players interact with the AI Dungeon Master. This replaces the placeholder game page with a fully functional UI showing message history, action input, character status, combat state, and death handling.

## Dependencies

- init-04-frontend-shell (React app structure, routing, API services)
- init-06-action-handler (POST /sessions/{id}/action endpoint)
- init-07-combat-system (Server-side combat, dice rolls in response)

## Goals

1. **Immersive chat experience** — Dark fantasy aesthetic, readable narrative
2. **Real-time status** — HP, XP, gold visible and updating after each action
3. **Combat visibility** — Dice rolls, enemy status, damage clearly shown
4. **Clear death state** — Game over screen when character dies
5. **Mobile-friendly** — Works on phone screens

## Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│  CHARACTER STATUS BAR                                        │
│  [Grimjaw - Fighter Lvl 1]  HP: 6/8  XP: 45  Gold: 120      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MESSAGE HISTORY (scrollable)                                │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [DM] You stand at the edge of the Dark Forest...    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [You] I draw my sword and proceed into the forest.  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [DM] A goblin leaps from the shadows!               │    │
│  │                                                      │    │
│  │ ⚔️ COMBAT                                            │    │
│  │ Your attack: d20(15)+2 = 17 vs AC 12 → HIT          │    │
│  │ Damage: d8(6)+2 = 8 → Goblin dies!                  │    │
│  │ +25 XP                                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  COMBAT STATUS (only when in combat)                         │
│  Enemies: Goblin (4/6 HP) | Orc (8/8 HP)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐  [Send]    │
│  │ Type your action...                         │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Component Structure

```
frontend/src/
├── pages/
│   └── GamePage.tsx              # MODIFY: Replace placeholder
├── components/
│   └── game/
│       ├── index.ts              # NEW: Barrel export
│       ├── ChatHistory.tsx       # NEW: Message list
│       ├── ChatMessage.tsx       # NEW: Single message bubble
│       ├── ActionInput.tsx       # NEW: Text input + send button
│       ├── CharacterStatus.tsx   # NEW: HP/XP/Gold bar
│       ├── CombatStatus.tsx      # NEW: Enemy list during combat
│       ├── DiceRoll.tsx          # NEW: Dice roll display
│       └── DeathScreen.tsx       # NEW: Game over overlay
├── hooks/
│   └── useGameSession.ts         # NEW: Game state management
├── types/
│   └── game.ts                   # MODIFY: Add UI-specific types
```

## Component Specifications

### GamePage.tsx

Main container that orchestrates the game UI.

```typescript
function GamePage() {
  const { sessionId } = useParams();
  const { 
    session, 
    character, 
    messages, 
    isLoading, 
    error,
    sendAction,
    isSessionEnded 
  } = useGameSession(sessionId);

  if (isSessionEnded) {
    return <DeathScreen character={character} session={session} />;
  }

  return (
    <div className="game-container">
      <CharacterStatus character={character} />
      <ChatHistory messages={messages} isLoading={isLoading} />
      {session?.combat_state?.active && (
        <CombatStatus enemies={session.combat_enemies} />
      )}
      <ActionInput onSend={sendAction} disabled={isLoading} />
    </div>
  );
}
```

### ChatHistory.tsx

Scrollable container for message history. Auto-scrolls to bottom on new messages.

```typescript
interface ChatHistoryProps {
  messages: GameMessage[];
  isLoading: boolean;
}

function ChatHistory({ messages, isLoading }: ChatHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-history">
      {messages.map((msg, idx) => (
        <ChatMessage key={idx} message={msg} />
      ))}
      {isLoading && <LoadingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
```

### ChatMessage.tsx

Individual message bubble with role-based styling.

```typescript
interface ChatMessageProps {
  message: GameMessage;
}

function ChatMessage({ message }: ChatMessageProps) {
  const isDM = message.role === 'dm';
  
  return (
    <div className={`message ${isDM ? 'dm' : 'player'}`}>
      <div className="message-header">
        {isDM ? '🎭 Dungeon Master' : '⚔️ You'}
      </div>
      <div className="message-content">
        {message.content}
      </div>
      {message.dice_rolls && message.dice_rolls.length > 0 && (
        <div className="dice-rolls">
          {message.dice_rolls.map((roll, idx) => (
            <DiceRoll key={idx} roll={roll} />
          ))}
        </div>
      )}
      {message.state_changes && (
        <StateChangeSummary changes={message.state_changes} />
      )}
    </div>
  );
}
```

### DiceRoll.tsx

Displays a single dice roll with visual flair.

```typescript
interface DiceRollProps {
  roll: {
    type: string;      // 'attack', 'damage', 'save'
    roll: number;      // natural roll
    modifier: number;
    total: number;
    success?: boolean;
  };
}

function DiceRoll({ roll }: DiceRollProps) {
  const isCrit = roll.roll === 20;
  const isFumble = roll.roll === 1;
  
  return (
    <div className={`dice-roll ${isCrit ? 'crit' : ''} ${isFumble ? 'fumble' : ''}`}>
      <span className="roll-type">{roll.type}:</span>
      <span className="roll-dice">d20({roll.roll})</span>
      {roll.modifier !== 0 && (
        <span className="roll-mod">
          {roll.modifier > 0 ? '+' : ''}{roll.modifier}
        </span>
      )}
      <span className="roll-total">= {roll.total}</span>
      {roll.success !== null && (
        <span className={`roll-result ${roll.success ? 'hit' : 'miss'}`}>
          → {roll.success ? 'HIT' : 'MISS'}
        </span>
      )}
    </div>
  );
}
```

### CharacterStatus.tsx

Persistent status bar showing character vitals.

```typescript
interface CharacterStatusProps {
  character: Character | null;
}

function CharacterStatus({ character }: CharacterStatusProps) {
  if (!character) return null;
  
  const hpPercent = (character.hp / character.max_hp) * 100;
  const hpColor = hpPercent > 50 ? 'green' : hpPercent > 25 ? 'yellow' : 'red';
  
  return (
    <div className="character-status">
      <div className="char-name">
        {character.name} - {character.character_class} Lvl {character.level}
      </div>
      <div className="char-stats">
        <div className="stat hp">
          <span className="label">HP:</span>
          <div className="hp-bar">
            <div 
              className={`hp-fill ${hpColor}`} 
              style={{ width: `${hpPercent}%` }} 
            />
          </div>
          <span className="value">{character.hp}/{character.max_hp}</span>
        </div>
        <div className="stat xp">
          <span className="label">XP:</span>
          <span className="value">{character.xp}</span>
        </div>
        <div className="stat gold">
          <span className="label">Gold:</span>
          <span className="value">{character.gold}</span>
        </div>
      </div>
    </div>
  );
}
```

### CombatStatus.tsx

Shows enemy status during active combat.

```typescript
interface CombatStatusProps {
  enemies: CombatEnemy[];
}

function CombatStatus({ enemies }: CombatStatusProps) {
  const livingEnemies = enemies.filter(e => e.hp > 0);
  
  if (livingEnemies.length === 0) return null;
  
  return (
    <div className="combat-status">
      <div className="combat-header">⚔️ IN COMBAT</div>
      <div className="enemy-list">
        {livingEnemies.map((enemy, idx) => (
          <div key={idx} className="enemy">
            <span className="enemy-name">{enemy.name}</span>
            <span className="enemy-hp">
              {enemy.hp}/{enemy.max_hp} HP
            </span>
            <span className="enemy-ac">AC {enemy.ac}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### ActionInput.tsx

Text input for player commands.

```typescript
interface ActionInputProps {
  onSend: (action: string) => void;
  disabled: boolean;
}

function ActionInput({ onSend, disabled }: ActionInputProps) {
  const [action, setAction] = useState('');
  
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (action.trim() && !disabled) {
      onSend(action.trim());
      setAction('');
    }
  };
  
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };
  
  return (
    <form className="action-input" onSubmit={handleSubmit}>
      <textarea
        value={action}
        onChange={(e) => setAction(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What do you do?"
        disabled={disabled}
        maxLength={500}
        rows={2}
      />
      <button type="submit" disabled={disabled || !action.trim()}>
        {disabled ? '...' : 'Send'}
      </button>
    </form>
  );
}
```

### DeathScreen.tsx

Game over overlay when character dies.

```typescript
interface DeathScreenProps {
  character: Character | null;
  session: Session | null;
}

function DeathScreen({ character, session }: DeathScreenProps) {
  const navigate = useNavigate();
  
  return (
    <div className="death-screen">
      <div className="death-content">
        <h1>☠️ YOU HAVE DIED ☠️</h1>
        <p className="death-message">
          {character?.name} has fallen in battle.
        </p>
        <p className="death-flavor">
          The darkness claims another soul...
        </p>
        <div className="death-stats">
          <div>Final Level: {character?.level}</div>
          <div>XP Earned: {character?.xp}</div>
          <div>Gold Collected: {character?.gold}</div>
        </div>
        <div className="death-actions">
          <button onClick={() => navigate('/characters/new')}>
            Create New Character
          </button>
          <button onClick={() => navigate('/characters')}>
            Back to Characters
          </button>
        </div>
      </div>
    </div>
  );
}
```

### useGameSession.ts Hook

Manages game state, loads session, sends actions.

```typescript
interface UseGameSessionReturn {
  session: Session | null;
  character: Character | null;
  messages: GameMessage[];
  isLoading: boolean;
  error: string | null;
  sendAction: (action: string) => Promise<void>;
  isSessionEnded: boolean;
}

function useGameSession(sessionId: string): UseGameSessionReturn {
  const [session, setSession] = useState<Session | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [messages, setMessages] = useState<GameMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSessionEnded, setIsSessionEnded] = useState(false);

  // Load session on mount
  useEffect(() => {
    loadSession();
  }, [sessionId]);

  const loadSession = async () => {
    try {
      setIsLoading(true);
      const sessionData = await sessionService.get(sessionId);
      const charData = await characterService.get(sessionData.character_id);
      
      setSession(sessionData);
      setCharacter(charData);
      setMessages(sessionData.message_history || []);
      setIsSessionEnded(sessionData.status === 'ended');
    } catch (err) {
      setError('Failed to load session');
    } finally {
      setIsLoading(false);
    }
  };

  const sendAction = async (action: string) => {
    if (isSessionEnded) return;
    
    try {
      setIsLoading(true);
      
      // Optimistically add player message
      const playerMsg: GameMessage = {
        role: 'player',
        content: action,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, playerMsg]);
      
      // Send to server
      const response = await sessionService.sendAction(sessionId, action);
      
      // Add DM response with dice rolls and state changes
      const dmMsg: GameMessage = {
        role: 'dm',
        content: response.narrative,
        timestamp: new Date().toISOString(),
        dice_rolls: response.dice_rolls,
        state_changes: response.state_changes,
      };
      setMessages(prev => [...prev, dmMsg]);
      
      // Update character from response
      if (response.character) {
        setCharacter(prev => prev ? { ...prev, ...response.character } : null);
      }
      
      // Update session combat state
      setSession(prev => prev ? {
        ...prev,
        combat_state: { active: response.combat_active },
        combat_enemies: response.enemies,
      } : null);
      
      // Check for death
      if (response.session_ended || response.character_dead) {
        setIsSessionEnded(true);
      }
      
    } catch (err: any) {
      if (err.status === 400 && err.message?.includes('ended')) {
        setIsSessionEnded(true);
      } else {
        setError('Failed to send action');
        // Remove optimistic message on error
        setMessages(prev => prev.slice(0, -1));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return {
    session,
    character,
    messages,
    isLoading,
    error,
    sendAction,
    isSessionEnded,
  };
}
```

## API Service Addition

Add to `services/sessions.ts`:

```typescript
export const sessionService = {
  // ... existing methods
  
  sendAction: (sessionId: string, action: string) =>
    request<ActionResponse>(`/sessions/${sessionId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),
};
```

## Types

Add to `types/game.ts`:

```typescript
interface GameMessage {
  role: 'player' | 'dm';
  content: string;
  timestamp: string;
  dice_rolls?: DiceRoll[];
  state_changes?: StateChanges;
}

interface DiceRoll {
  type: string;
  roll: number;
  modifier: number;
  total: number;
  success?: boolean;
}

interface StateChanges {
  hp_delta?: number;
  gold_delta?: number;
  xp_delta?: number;
  location?: string;
  inventory_add?: string[];
  inventory_remove?: string[];
}

interface CombatEnemy {
  id: string;
  name: string;
  hp: number;
  max_hp: number;
  ac: number;
}

interface ActionResponse {
  narrative: string;
  state_changes: StateChanges;
  dice_rolls: DiceRoll[];
  combat_active: boolean;
  enemies: CombatEnemy[];
  character: CharacterSnapshot;
  character_dead: boolean;
  session_ended: boolean;
}

interface CharacterSnapshot {
  hp: number;
  max_hp: number;
  xp: number;
  gold: number;
  level: number;
  inventory: string[];
}
```

## Styling Requirements

Use Tailwind CSS with dark fantasy theme:

- **Background**: Dark grays (`bg-gray-900`, `bg-gray-800`)
- **Text**: Light (`text-gray-100`, `text-gray-300`)
- **Accents**: Gold/amber for highlights (`text-amber-500`)
- **DM messages**: Slightly different background (`bg-gray-800`)
- **Player messages**: Distinct style (`bg-gray-700`, right-aligned or different border)
- **HP bar**: Green → Yellow → Red gradient based on percentage
- **Combat**: Red accent border when in combat
- **Death screen**: Dark overlay with skull imagery

### Key Tailwind Classes

```css
/* Chat container */
.chat-history: h-[60vh] overflow-y-auto flex flex-col gap-4 p-4

/* Message bubbles */
.message.dm: bg-gray-800 rounded-lg p-4 border-l-4 border-amber-600
.message.player: bg-gray-700 rounded-lg p-4 border-l-4 border-blue-600

/* HP bar */
.hp-bar: w-24 h-3 bg-gray-700 rounded-full overflow-hidden
.hp-fill.green: bg-green-500
.hp-fill.yellow: bg-yellow-500
.hp-fill.red: bg-red-500

/* Combat status */
.combat-status: bg-red-900/30 border border-red-700 rounded-lg p-3

/* Death screen */
.death-screen: fixed inset-0 bg-black/90 flex items-center justify-center
.death-content: bg-gray-900 border-2 border-red-800 rounded-lg p-8 text-center
```

## Mobile Responsiveness

- Stack layout vertically on small screens
- Larger touch targets for buttons
- Collapsible character status on very small screens
- Full-width action input
- Minimum viable: 320px width

## Loading States

1. **Initial load**: Skeleton UI for message history
2. **Sending action**: Disable input, show "..." on button, add typing indicator
3. **Error**: Toast notification, re-enable input

## Acceptance Criteria

- [ ] Chat history displays all messages from session
- [ ] Messages auto-scroll to bottom on new content
- [ ] Player can type and send actions
- [ ] Enter key sends action (Shift+Enter for newline)
- [ ] DM responses appear with narrative text
- [ ] Dice rolls display with roll/modifier/total breakdown
- [ ] Character status bar shows HP/XP/Gold
- [ ] HP bar changes color based on health percentage
- [ ] Combat status shows living enemies during combat
- [ ] Death screen appears when character dies
- [ ] Dead session blocks further input
- [ ] Mobile responsive (works on 375px width)
- [ ] Loading states for all async operations
- [ ] Error handling with user feedback

## Testing Requirements

### Unit Tests
- `ChatMessage` renders DM vs player styles correctly
- `DiceRoll` shows crit/fumble styling
- `CharacterStatus` calculates HP percentage correctly
- `DeathScreen` displays final stats

### Integration Tests
- `useGameSession` loads session data correctly
- `sendAction` updates messages and character state
- Session ended state is detected

### Manual Testing
1. Load game page with existing session
2. See message history from previous actions
3. Type action and submit
4. See DM response appear
5. Verify dice rolls display during combat
6. Verify HP/XP/Gold update after action
7. Die in combat, see death screen
8. Verify navigation buttons work on death screen
9. Test on mobile viewport

## Out of Scope

- Sound effects
- Animations (beyond basic CSS transitions)
- Inventory management UI (init-10)
- Character sheet popup (init-15)
- Settings/options menu
- Save/load (sessions auto-save)

## Notes

- Keep messages in memory; session.message_history is source of truth on reload
- Consider message virtualization if history gets very long (future optimization)
- Dice roll animations could be added later as polish
