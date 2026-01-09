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
  CombatAction,
  CombatResponse,
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
  /** Combat UI state (turn-based combat) */
  combat: CombatResponse | null;
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
  /** Send a player action to the DM (free text or with combat action) */
  sendAction: (action: string, combatAction?: CombatAction) => Promise<void>;
  /** Send a combat action (convenience wrapper) */
  sendCombatAction: (combatAction: CombatAction) => Promise<void>;
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
  const [combat, setCombat] = useState<CombatResponse | null>(null);
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
   *
   * @param action - Free text action description
   * @param combatAction - Optional structured combat action for turn-based combat
   */
  const sendAction = useCallback(
    async (action: string, combatAction?: CombatAction) => {
      if (isSendingAction || sessionEnded || characterDead) {
        return;
      }

      const trimmedAction = action.trim();
      if (!trimmedAction && !combatAction) return;

      setIsSendingAction(true);
      setError(null);

      // Optimistically add player message
      // Use combat enemies for resolving target names in action labels
      const combatEnemies = combat?.enemies;
      const playerMessage: GameMessage = {
        role: 'player',
        content: trimmedAction || getCombatActionLabel(combatAction, combatEnemies),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, playerMessage]);

      try {
        const response = await sessionService.sendAction(
          sessionId,
          trimmedAction || getCombatActionLabel(combatAction, combatEnemies),
          combatAction
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

        // Update turn-based combat UI state
        if (response.combat) {
          console.log('[useGameSession] Combat response FULL:', JSON.stringify(response.combat, null, 2));
          setCombat(response.combat);
        } else if (!response.combat_active) {
          // Combat ended, clear combat state
          setCombat(null);
        }

        // Check for death/session end
        if (response.character_dead) {
          console.log('[useGameSession] Character died! FULL response:', JSON.stringify(response, null, 2));
          console.log('[useGameSession] dice_rolls array:', response.dice_rolls);
          console.log('[useGameSession] dice_rolls length:', response.dice_rolls?.length);
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
    [sessionId, isSendingAction, sessionEnded, characterDead, combat]
  );

  /**
   * Convenience wrapper for sending combat actions.
   * Generates a text label for the action for the chat history.
   */
  const sendCombatAction = useCallback(
    async (combatAction: CombatAction) => {
      const actionLabel = getCombatActionLabel(combatAction, combat?.enemies);
      await sendAction(actionLabel, combatAction);
    },
    [sendAction, combat]
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
    combat,
    characterDead,
    sessionEnded,
    isLoading,
    isSendingAction,
    error,
    usage,
    sendAction,
    sendCombatAction,
    clearError,
    retryLoad,
  };
}

/**
 * Get a human-readable label for a combat action.
 * @param action - The combat action
 * @param enemies - List of enemies to resolve target names
 */
function getCombatActionLabel(
  action?: CombatAction,
  enemies?: CombatEnemy[]
): string {
  if (!action) return '';

  switch (action.action_type) {
    case 'attack': {
      if (!action.target_id) return 'Attack';
      // Look up enemy name from enemies list
      const target = enemies?.find((e) => e.id === action.target_id);
      const targetName = target?.name || 'enemy';
      return `Attack ${targetName}`;
    }
    case 'defend':
      return 'Defend';
    case 'flee':
      return 'Flee';
    case 'use_item':
      return action.item_id ? `Use ${action.item_id}` : 'Use item';
    default:
      return 'Action';
  }
}
