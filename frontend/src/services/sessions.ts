/**
 * Session API service.
 */
import { request, getUserId } from './api';
import {
  Session,
  SessionListResponse,
  SessionCreateRequest,
  SessionCreateResponse,
  MessageHistoryResponse,
  FullActionResponse,
  LimitReachedResponse,
  ApiRequestError,
  CombatAction,
  GameOptions,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const sessionService = {
  /**
   * List sessions, optionally filtered by character.
   */
  list: (characterId?: string) => {
    const query = characterId ? `?character_id=${characterId}` : '';
    return request<SessionListResponse>(`/sessions${query}`);
  },

  /**
   * Get a single session by ID.
   */
  get: (id: string) => request<Session>(`/sessions/${id}`),

  /**
   * Create a new game session.
   */
  create: (data: SessionCreateRequest) =>
    request<SessionCreateResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /**
   * Get paginated message history for a session.
   */
  getHistory: (id: string, limit = 20, before?: string) => {
    let query = `?limit=${limit}`;
    if (before) query += `&before=${before}`;
    return request<MessageHistoryResponse>(`/sessions/${id}/history${query}`);
  },

  /**
   * Delete a session.
   */
  delete: (id: string) =>
    request<void>(`/sessions/${id}`, { method: 'DELETE' }),

  /**
   * Send a player action to the DM.
   * Returns LimitReachedResponse if token limits are hit (429).
   *
   * @param sessionId - The session ID
   * @param action - Free-text action (used outside combat or as fallback)
   * @param combatAction - Structured combat action (used during combat)
   */
  sendAction: async (
    sessionId: string,
    action: string,
    combatAction?: CombatAction
  ): Promise<FullActionResponse | LimitReachedResponse> => {
    const userId = getUserId();

    // Build request body
    const body: { action: string; combat_action?: CombatAction } = { action };
    if (combatAction) {
      body.combat_action = combatAction;
    }

    const response = await fetch(`${API_BASE}/sessions/${sessionId}/action`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId,
      },
      body: JSON.stringify(body),
    });

    // Handle 429 as a valid response (has narrative message)
    if (response.status === 429) {
      return response.json() as Promise<LimitReachedResponse>;
    }

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ error: 'Unknown error' }));
      throw new ApiRequestError(response.status, error.error, error.details);
    }

    return response.json() as Promise<FullActionResponse>;
  },

  /**
   * Update session options (gore level, mature content, combat confirmation).
   */
  updateOptions: (sessionId: string, options: GameOptions) =>
    request<{ options: GameOptions }>(`/sessions/${sessionId}/options`, {
      method: 'PATCH',
      body: JSON.stringify(options),
    }),
};
