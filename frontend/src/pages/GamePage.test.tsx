/**
 * Tests for GamePage component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { GamePage } from './GamePage';
import { sessionService } from '../services/sessions';
import { characterService } from '../services/characters';

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

function renderGamePage(sessionId: string) {
  return render(
    <MemoryRouter initialEntries={[`/play/${sessionId}`]}>
      <Routes>
        <Route path="/play/:sessionId" element={<GamePage />} />
      </Routes>
    </MemoryRouter>
  );
}

const mockSession = {
  session_id: 'test-session-123',
  user_id: 'user-1',
  character_id: 'char-1',
  campaign_setting: 'default',
  current_location: 'Town Square',
  world_state: {},
  message_history: [
    { role: 'dm' as const, content: 'Welcome to the dungeon!', timestamp: '2024-01-01T00:00:00Z' },
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

describe('GamePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (sessionService.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockSession);
    (characterService.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockCharacter);
  });

  it('shows loading state initially', () => {
    renderGamePage('test-session-123');
    expect(screen.getByText('Loading adventure...')).toBeInTheDocument();
  });

  it('displays character name after loading', async () => {
    renderGamePage('test-session-123');

    await waitFor(() => {
      expect(screen.getByText('Thorin')).toBeInTheDocument();
    });
  });

  it('displays character class and level', async () => {
    renderGamePage('test-session-123');

    await waitFor(() => {
      expect(screen.getByText(/Fighter/)).toBeInTheDocument();
      expect(screen.getByText(/Level 1/)).toBeInTheDocument();
    });
  });

  it('displays message history', async () => {
    renderGamePage('test-session-123');

    await waitFor(() => {
      expect(screen.getByText('Welcome to the dungeon!')).toBeInTheDocument();
    });
  });

  it('displays HP, XP, and Gold values', async () => {
    renderGamePage('test-session-123');

    await waitFor(() => {
      expect(screen.getByText('10/10')).toBeInTheDocument(); // HP
      expect(screen.getByText('0')).toBeInTheDocument(); // XP
      expect(screen.getByText('50')).toBeInTheDocument(); // Gold
    });
  });

  it('shows error state when session not found', async () => {
    const { ApiRequestError } = await import('../types');
    (sessionService.get as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiRequestError(404, 'Not found')
    );

    renderGamePage('bad-session');

    await waitFor(() => {
      expect(screen.getByText('Failed to Load Session')).toBeInTheDocument();
    });
  });

  it('shows action input when loaded', async () => {
    renderGamePage('test-session-123');

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/what do you do/i)).toBeInTheDocument();
    });
  });

  it('shows send button when loaded', async () => {
    renderGamePage('test-session-123');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    });
  });
});
