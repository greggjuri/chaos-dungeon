/**
 * Session API service.
 */
import { request } from './api';
import {
  Session,
  SessionListResponse,
  SessionCreateRequest,
  SessionCreateResponse,
  MessageHistoryResponse,
  FullActionResponse,
} from '../types';

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
   */
  sendAction: (sessionId: string, action: string) =>
    request<FullActionResponse>(`/sessions/${sessionId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),
};
