/**
 * Character API service.
 */
import { request } from './api';
import {
  Character,
  CharacterListResponse,
  CreateCharacterRequest,
} from '../types';

export const characterService = {
  /**
   * List all characters for current user.
   */
  list: () => request<CharacterListResponse>('/characters'),

  /**
   * Get a single character by ID.
   */
  get: (id: string) => request<Character>(`/characters/${id}`),

  /**
   * Create a new character.
   */
  create: (data: CreateCharacterRequest) =>
    request<Character>('/characters', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /**
   * Delete a character.
   */
  delete: (id: string) =>
    request<void>(`/characters/${id}`, { method: 'DELETE' }),
};
