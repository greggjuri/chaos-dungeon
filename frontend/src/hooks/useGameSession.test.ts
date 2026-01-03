/**
 * Tests for useGameSession hook.
 */
import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useGameSession } from './useGameSession';
import { sessionService } from '../services/sessions';
import { characterService } from '../services/characters';
import { ApiRequestError } from '../types';

// Mock the services
vi.mock('../services/sessions', () => ({
  sessionService: {
    get: vi.fn(),
    sendAction: vi.fn(),
  },
}));

vi.mock('../services/characters', () => ({
  characterService: {
    get: vi.fn(),
  },
}));

describe('useGameSession', () => {
  const mockSession = {
    session_id: 'session-1',
    user_id: 'user-1',
    character_id: 'char-1',
    campaign_setting: 'default',
    current_location: 'Town Square',
    world_state: {},
    message_history: [
      { role: 'dm' as const, content: 'Welcome!', timestamp: '2024-01-01T00:00:00Z' },
    ],
    created_at: '2024-01-01T00:00:00Z',
  };

  const mockCharacter = {
    character_id: 'char-1',
    user_id: 'user-1',
    name: 'Thorin',
    character_class: 'fighter' as const,
    level: 1,
    xp: 0,
    hp: 10,
    max_hp: 10,
    gold: 50,
    abilities: {
      strength: 14,
      intelligence: 10,
      wisdom: 12,
      dexterity: 13,
      constitution: 15,
      charisma: 8,
    },
    inventory: [],
    created_at: '2024-01-01T00:00:00Z',
  };

  const mockActionResponse = {
    narrative: 'You search the room and find nothing.',
    state_changes: {
      hp_delta: 0,
      gold_delta: 0,
      xp_delta: 10,
      location: null,
      inventory_add: [],
      inventory_remove: [],
      world_state: {},
    },
    dice_rolls: [],
    combat_active: false,
    enemies: [],
    character: {
      hp: 10,
      max_hp: 10,
      xp: 10,
      gold: 50,
      level: 1,
      inventory: [],
    },
    character_dead: false,
    session_ended: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (sessionService.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockSession);
    (characterService.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockCharacter);
    (sessionService.sendAction as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockActionResponse
    );
  });

  it('loads session and character on mount', async () => {
    const { result } = renderHook(() => useGameSession('session-1'));

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.session).toEqual(mockSession);
    expect(result.current.character).toEqual(mockCharacter);
    expect(result.current.messages).toHaveLength(1);
  });

  it('sets error when session not found', async () => {
    (sessionService.get as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiRequestError(404, 'Not found')
    );

    const { result } = renderHook(() => useGameSession('bad-session'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Session not found. It may have been deleted.');
    expect(result.current.session).toBeNull();
  });

  it('sends action and updates messages', async () => {
    const { result } = renderHook(() => useGameSession('session-1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.sendAction('I search the room');
    });

    // Should have original message + player message + DM response
    expect(result.current.messages).toHaveLength(3);
    expect(result.current.messages[1].role).toBe('player');
    expect(result.current.messages[1].content).toBe('I search the room');
    expect(result.current.messages[2].role).toBe('dm');
    expect(result.current.messages[2].content).toBe('You search the room and find nothing.');
  });

  it('updates character snapshot after action', async () => {
    const { result } = renderHook(() => useGameSession('session-1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.sendAction('action');
    });

    expect(result.current.characterSnapshot?.xp).toBe(10);
  });

  it('sets characterDead when character dies', async () => {
    (sessionService.sendAction as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockActionResponse,
      character_dead: true,
      character: { ...mockActionResponse.character, hp: 0 },
    });

    const { result } = renderHook(() => useGameSession('session-1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.sendAction('action');
    });

    expect(result.current.characterDead).toBe(true);
    expect(result.current.sessionEnded).toBe(true);
  });

  it('updates combat state from response', async () => {
    (sessionService.sendAction as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockActionResponse,
      combat_active: true,
      enemies: [{ name: 'Goblin', hp: 5, max_hp: 5, ac: 12 }],
    });

    const { result } = renderHook(() => useGameSession('session-1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.sendAction('I attack the goblin');
    });

    expect(result.current.combatActive).toBe(true);
    expect(result.current.enemies).toHaveLength(1);
  });

  it('removes optimistic message on error', async () => {
    (sessionService.sendAction as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiRequestError(500, 'Server error')
    );

    const { result } = renderHook(() => useGameSession('session-1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const initialMessageCount = result.current.messages.length;

    await act(async () => {
      await result.current.sendAction('action');
    });

    // Message count should be same as before (optimistic message removed)
    expect(result.current.messages).toHaveLength(initialMessageCount);
    expect(result.current.error).toBe('Server error');
  });

  it('clears error when clearError is called', async () => {
    (sessionService.sendAction as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiRequestError(500, 'Server error')
    );

    const { result } = renderHook(() => useGameSession('session-1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.sendAction('action');
    });

    expect(result.current.error).toBe('Server error');

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });

  it('does not send action when session is ended', async () => {
    (sessionService.sendAction as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockActionResponse,
      session_ended: true,
    });

    const { result } = renderHook(() => useGameSession('session-1'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // First action ends the session
    await act(async () => {
      await result.current.sendAction('action');
    });

    vi.clearAllMocks();

    // Second action should be blocked
    await act(async () => {
      await result.current.sendAction('another action');
    });

    expect(sessionService.sendAction).not.toHaveBeenCalled();
  });
});
