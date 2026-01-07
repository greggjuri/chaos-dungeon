/**
 * Hook for managing game session state and actions.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { sessionService } from '../services/sessions';
import { characterService } from '../services/characters';
import {
  Session,
  Character,
  GameMessage,
  CharacterSnapshot,
  CombatEnemy,
  UsageStats,
  ApiRequestError,
  isLimitReached,
} from '../types';

interface GameState {
  /** Current session data */
  session: Session | null;
  /** Full character data */
  character: Character | null;
  /** Character snapshot (updated after each action) */
  characterSnapshot: CharacterSnapshot | null;
  /** Message history with dice rolls and state changes */
  messages: GameMessage[];
  /** Whether we're in active combat */
  combatActive: boolean;
  /** Living enemies in combat */
  enemies: CombatEnemy[];
  /** Whether the character is dead */
  characterDead: boolean;
  /** Whether the session has ended */
  sessionEnded: boolean;
  /** Loading states */
  isLoading: boolean;
  isSendingAction: boolean;
  /** Error state */
  error: string | null;
  /** Token usage statistics (for debugging) */
  usage: UsageStats | null;
}

interface UseGameSessionReturn extends GameState {
  /** Send a player action to the DM */
  sendAction: (action: string) => Promise<void>;
  /** Clear the error state */
  clearError: () => void;
  /** Retry loading the session */
  retryLoad: () => void;
}

/**
 * Hook for managing a game session.
 *
 * Handles loading session and character data, sending actions with
 * optimistic updates, and tracking game state like combat and death.
 *
 * @param sessionId - The session ID to load
 * @returns Game state and action handlers
 */
export function useGameSession(sessionId: string): UseGameSessionReturn {
  const [session, setSession] = useState<Session | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [characterSnapshot, setCharacterSnapshot] =
    useState<CharacterSnapshot | null>(null);
  const [messages, setMessages] = useState<GameMessage[]>([]);
  const [combatActive, setCombatActive] = useState(false);
  const [enemies, setEnemies] = useState<CombatEnemy[]>([]);
  const [characterDead, setCharacterDead] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSendingAction, setIsSendingAction] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);

  // Track if we're currently loading to prevent duplicate requests
  const loadingRef = useRef(false);

  /**
   * Load session and character data.
   */
  const loadSession = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;

    setIsLoading(true);
    setError(null);

    try {
      // Load session first
      const sessionData = await sessionService.get(sessionId);
      setSession(sessionData);

      // Convert message history to GameMessage format
      const gameMessages: GameMessage[] = sessionData.message_history.map(
        (msg) => ({
          ...msg,
          dice_rolls: undefined,
          state_changes: undefined,
        })
      );
      setMessages(gameMessages);

      // Load character data
      const characterData = await characterService.get(
        sessionData.character_id
      );
      setCharacter(characterData);

      // Initialize character snapshot from full character
      setCharacterSnapshot({
        hp: characterData.hp,
        max_hp: characterData.max_hp,
        xp: characterData.xp,
        gold: characterData.gold,
        level: characterData.level,
        inventory: characterData.inventory.map((item) => item.name),
      });

      // Check if character is already dead
      if (characterData.hp <= 0) {
        setCharacterDead(true);
        setSessionEnded(true);
      }
    } catch (err) {
      if (err instanceof ApiRequestError) {
        if (err.status === 404) {
          setError('Session not found. It may have been deleted.');
        } else {
          setError(err.error || 'Failed to load session');
        }
      } else {
        setError('Failed to load session');
      }
    } finally {
      setIsLoading(false);
      loadingRef.current = false;
    }
  }, [sessionId]);

  // Load on mount
  useEffect(() => {
    loadSession();
  }, [loadSession]);

  /**
   * Send a player action to the DM.
   * Uses optimistic updates - adds the player message immediately,
   * then updates with the response or rolls back on error.
   */
  const sendAction = useCallback(
    async (action: string) => {
      if (isSendingAction || sessionEnded || characterDead) {
        return;
      }

      const trimmedAction = action.trim();
      if (!trimmedAction) return;

      setIsSendingAction(true);
      setError(null);

      // Optimistically add player message
      const playerMessage: GameMessage = {
        role: 'player',
        content: trimmedAction,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, playerMessage]);

      try {
        const response = await sessionService.sendAction(
          sessionId,
          trimmedAction
        );

        // Handle limit reached response (429)
        if (isLimitReached(response)) {
          // Add the limit message as a DM response
          const dmMessage: GameMessage = {
            role: 'dm',
            content: response.message,
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, dmMessage]);
          return;
        }

        // Normal action response
        // Add DM response message
        const dmMessage: GameMessage = {
          role: 'dm',
          content: response.narrative,
          timestamp: new Date().toISOString(),
          dice_rolls: response.dice_rolls,
          state_changes: response.state_changes,
        };
        setMessages((prev) => [...prev, dmMessage]);

        // Update character snapshot
        setCharacterSnapshot(response.character);

        // Update usage stats if available
        if (response.usage) {
          setUsage(response.usage);
        }

        // Update combat state
        setCombatActive(response.combat_active);
        setEnemies(response.enemies.filter((e) => e.hp > 0));

        // Check for death/session end
        if (response.character_dead) {
          setCharacterDead(true);
          setSessionEnded(true);
        } else if (response.session_ended) {
          setSessionEnded(true);
        }
      } catch (err) {
        // Remove the optimistic player message on error
        setMessages((prev) => prev.slice(0, -1));

        if (err instanceof ApiRequestError) {
          if (err.status === 400 && err.error?.includes('ended')) {
            setSessionEnded(true);
            setError('This session has ended.');
          } else {
            setError(err.error || 'Failed to send action');
          }
        } else {
          setError('Failed to send action. Please try again.');
        }
      } finally {
        setIsSendingAction(false);
      }
    },
    [sessionId, isSendingAction, sessionEnded, characterDead]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const retryLoad = useCallback(() => {
    loadingRef.current = false;
    loadSession();
  }, [loadSession]);

  return {
    session,
    character,
    characterSnapshot,
    messages,
    combatActive,
    enemies,
    characterDead,
    sessionEnded,
    isLoading,
    isSendingAction,
    error,
    usage,
    sendAction,
    clearError,
    retryLoad,
  };
}
