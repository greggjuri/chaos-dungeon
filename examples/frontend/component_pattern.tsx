/**
 * Example React component pattern for Chaos Dungeon.
 *
 * This demonstrates:
 * - TypeScript interfaces for props
 * - Functional component with hooks
 * - Tailwind CSS styling
 * - Error handling
 * - Loading states
 */
import { useCallback, useState } from 'react';

/**
 * Props interface with JSDoc descriptions.
 */
interface GameMessageProps {
  /** The message content to display */
  content: string;
  /** Who sent the message */
  role: 'player' | 'dm';
  /** When the message was sent */
  timestamp: string;
  /** Optional dice rolls included in the message */
  diceRolls?: DiceRoll[];
  /** Optional callback when message is clicked */
  onClick?: () => void;
}

interface DiceRoll {
  type: string; // e.g., "d20", "2d6"
  result: number;
  modifier?: number;
  success?: boolean;
}

/**
 * Displays a single game message from player or DM.
 *
 * @example
 * <GameMessage
 *   content="You enter the dark cavern..."
 *   role="dm"
 *   timestamp="2025-01-01T12:00:00Z"
 * />
 */
export function GameMessage({
  content,
  role,
  timestamp,
  diceRolls,
  onClick,
}: GameMessageProps) {
  // Format timestamp for display
  const formattedTime = new Date(timestamp).toLocaleTimeString();

  // Style based on role
  const containerClasses = `
    p-4 rounded-lg mb-2 cursor-pointer transition-colors
    ${role === 'dm'
      ? 'bg-slate-800 text-slate-100 border-l-4 border-amber-500'
      : 'bg-slate-700 text-slate-200 ml-8'
    }
  `;

  return (
    <div
      className={containerClasses}
      onClick={onClick}
      role="article"
      aria-label={`${role === 'dm' ? 'Dungeon Master' : 'Player'} message`}
    >
      {/* Header with role and time */}
      <div className="flex justify-between items-center mb-2 text-sm">
        <span className="font-semibold text-amber-400">
          {role === 'dm' ? '🎭 Dungeon Master' : '⚔️ You'}
        </span>
        <span className="text-slate-400">{formattedTime}</span>
      </div>

      {/* Message content */}
      <p className="whitespace-pre-wrap leading-relaxed">{content}</p>

      {/* Dice rolls if present */}
      {diceRolls && diceRolls.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {diceRolls.map((roll, index) => (
            <DiceRollBadge key={index} roll={roll} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Badge showing a dice roll result.
 */
function DiceRollBadge({ roll }: { roll: DiceRoll }) {
  const bgColor = roll.success === undefined
    ? 'bg-slate-600'
    : roll.success
      ? 'bg-green-700'
      : 'bg-red-700';

  return (
    <span className={`${bgColor} px-2 py-1 rounded text-sm font-mono`}>
      🎲 {roll.type}: {roll.result}
      {roll.modifier !== undefined && (
        <span className="text-slate-300">
          {roll.modifier >= 0 ? '+' : ''}{roll.modifier}
        </span>
      )}
    </span>
  );
}

// --- Example of a component with state and effects ---

interface GameInputProps {
  /** Callback when user submits an action */
  onSubmit: (action: string) => Promise<void>;
  /** Whether input should be disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
}

/**
 * Input component for player actions.
 *
 * Handles form submission, loading state, and error display.
 */
export function GameInput({
  onSubmit,
  disabled = false,
  placeholder = 'What do you do?',
}: GameInputProps) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedInput = input.trim();
    if (!trimmedInput) return;

    setIsLoading(true);
    setError(null);

    try {
      await onSubmit(trimmedInput);
      setInput(''); // Clear on success
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [input, onSubmit]);

  return (
    <form onSubmit={handleSubmit} className="mt-4">
      {/* Error display */}
      {error && (
        <div className="mb-2 p-2 bg-red-900/50 border border-red-500 rounded text-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Input field */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          className="
            flex-1 px-4 py-2 rounded-lg
            bg-slate-700 border border-slate-600
            text-slate-100 placeholder-slate-400
            focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed
          "
          aria-label="Enter your action"
        />

        <button
          type="submit"
          disabled={disabled || isLoading || !input.trim()}
          className="
            px-6 py-2 rounded-lg font-semibold
            bg-amber-600 hover:bg-amber-500 text-white
            transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <LoadingSpinner />
              Thinking...
            </span>
          ) : (
            'Send'
          )}
        </button>
      </div>

      {/* Character counter */}
      <div className="mt-1 text-right text-xs text-slate-500">
        {input.length} / 500
      </div>
    </form>
  );
}

/**
 * Simple loading spinner component.
 */
function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

// Default export for main component
export default GameMessage;
