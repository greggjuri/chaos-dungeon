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
   */
  sendAction: async (
    sessionId: string,
    action: string
  ): Promise<FullActionResponse | LimitReachedResponse> => {
    const userId = getUserId();

    const response = await fetch(`${API_BASE}/sessions/${sessionId}/action`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId,
      },
      body: JSON.stringify({ action }),
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
};
