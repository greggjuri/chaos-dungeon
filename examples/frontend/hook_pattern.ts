/**
 * Example custom hook patterns for Chaos Dungeon.
 *
 * This demonstrates:
 * - TypeScript generics with hooks
 * - Error handling patterns
 * - Loading states
 * - API integration
 */
import { useCallback, useEffect, useReducer, useState } from 'react';

// --- API Types ---

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

interface Character {
  id: string;
  name: string;
  characterClass: 'fighter' | 'thief' | 'mage' | 'cleric';
  level: number;
  hp: number;
  maxHp: number;
  gold: number;
}

interface GameSession {
  id: string;
  characterId: string;
  location: string;
  messages: Message[];
}

interface Message {
  role: 'player' | 'dm';
  content: string;
  timestamp: string;
}

// --- Generic Fetch Hook ---

/**
 * Generic hook for fetching data from API.
 *
 * @example
 * const { data, error, loading, refetch } = useFetch<Character>('/api/characters/123');
 */
export function useFetch<T>(url: string): ApiResponse<T> & { refetch: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();
      setData(json);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, error, loading, refetch: fetchData };
}

// --- Game State Hook ---

interface GameState {
  session: GameSession | null;
  character: Character | null;
  messages: Message[];
  isProcessing: boolean;
  error: string | null;
}

type GameAction =
  | { type: 'SET_SESSION'; payload: GameSession }
  | { type: 'SET_CHARACTER'; payload: Character }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'SET_PROCESSING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'UPDATE_CHARACTER'; payload: Partial<Character> }
  | { type: 'RESET' };

function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'SET_SESSION':
      return {
        ...state,
        session: action.payload,
        messages: action.payload.messages,
      };

    case 'SET_CHARACTER':
      return { ...state, character: action.payload };

    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };

    case 'SET_PROCESSING':
      return { ...state, isProcessing: action.payload };

    case 'SET_ERROR':
      return { ...state, error: action.payload };

    case 'UPDATE_CHARACTER':
      if (!state.character) return state;
      return {
        ...state,
        character: { ...state.character, ...action.payload },
      };

    case 'RESET':
      return initialGameState;

    default:
      return state;
  }
}

const initialGameState: GameState = {
  session: null,
  character: null,
  messages: [],
  isProcessing: false,
  error: null,
};

/**
 * Main game state hook.
 *
 * Manages the entire game state including session, character,
 * messages, and player actions.
 *
 * @example
 * const { state, sendAction, loadSession } = useGameState();
 */
export function useGameState(apiBaseUrl: string = '/api') {
  const [state, dispatch] = useReducer(gameReducer, initialGameState);

  /**
   * Load an existing game session.
   */
  const loadSession = useCallback(async (sessionId: string) => {
    dispatch({ type: 'SET_PROCESSING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      const response = await fetch(`${apiBaseUrl}/sessions/${sessionId}`);

      if (!response.ok) {
        throw new Error('Failed to load session');
      }

      const session: GameSession = await response.json();
      dispatch({ type: 'SET_SESSION', payload: session });

      // Also load the character
      const charResponse = await fetch(
        `${apiBaseUrl}/characters/${session.characterId}`
      );

      if (charResponse.ok) {
        const character: Character = await charResponse.json();
        dispatch({ type: 'SET_CHARACTER', payload: character });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      dispatch({ type: 'SET_ERROR', payload: message });
    } finally {
      dispatch({ type: 'SET_PROCESSING', payload: false });
    }
  }, [apiBaseUrl]);

  /**
   * Send a player action to the DM.
   */
  const sendAction = useCallback(async (action: string) => {
    if (!state.session) {
      throw new Error('No active session');
    }

    dispatch({ type: 'SET_PROCESSING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    // Optimistically add player message
    const playerMessage: Message = {
      role: 'player',
      content: action,
      timestamp: new Date().toISOString(),
    };
    dispatch({ type: 'ADD_MESSAGE', payload: playerMessage });

    try {
      const response = await fetch(
        `${apiBaseUrl}/sessions/${state.session.id}/action`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to process action');
      }

      const result = await response.json();

      // Add DM response
      const dmMessage: Message = {
        role: 'dm',
        content: result.narrative,
        timestamp: new Date().toISOString(),
      };
      dispatch({ type: 'ADD_MESSAGE', payload: dmMessage });

      // Update character if state changed
      if (result.stateChanges) {
        dispatch({ type: 'UPDATE_CHARACTER', payload: result.stateChanges });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      dispatch({ type: 'SET_ERROR', payload: message });
      throw err; // Re-throw for component error handling
    } finally {
      dispatch({ type: 'SET_PROCESSING', payload: false });
    }
  }, [apiBaseUrl, state.session]);

  /**
   * Create a new game session.
   */
  const createSession = useCallback(async (characterId: string) => {
    dispatch({ type: 'SET_PROCESSING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      const response = await fetch(`${apiBaseUrl}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ characterId }),
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const session: GameSession = await response.json();
      dispatch({ type: 'SET_SESSION', payload: session });

      return session;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      dispatch({ type: 'SET_ERROR', payload: message });
      throw err;
    } finally {
      dispatch({ type: 'SET_PROCESSING', payload: false });
    }
  }, [apiBaseUrl]);

  /**
   * Reset the game state.
   */
  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    state,
    sendAction,
    loadSession,
    createSession,
    reset,
  };
}

// --- Local Storage Hook ---

/**
 * Hook for persisting state in localStorage.
 *
 * @example
 * const [userId, setUserId] = useLocalStorage('userId', generateId());
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  // Get initial value from localStorage or use default
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  // Update localStorage when value changes
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const newValue = value instanceof Function ? value(prev) : value;
        try {
          window.localStorage.setItem(key, JSON.stringify(newValue));
        } catch (err) {
          console.error('Failed to save to localStorage:', err);
        }
        return newValue;
      });
    },
    [key]
  );

  return [storedValue, setValue];
}

// Default export
export default useGameState;
