/**
 * Tests for DeathScreen component.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { DeathScreen } from './DeathScreen';
import { Character } from '../../types';

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('DeathScreen', () => {
  const mockCharacter: Character = {
    character_id: 'char-1',
    user_id: 'user-1',
    name: 'Thorin',
    character_class: 'fighter',
    level: 3,
    xp: 4500,
    hp: 0,
    max_hp: 25,
    gold: 150,
    abilities: {
      strength: 16,
      intelligence: 10,
      wisdom: 12,
      dexterity: 14,
      constitution: 15,
      charisma: 8,
    },
    inventory: [],
    created_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('displays death message with character name', () => {
    render(
      <BrowserRouter>
        <DeathScreen character={mockCharacter} snapshot={null} />
      </BrowserRouter>
    );

    expect(screen.getByText('YOU HAVE DIED')).toBeInTheDocument();
    expect(
      screen.getByText(/Thorin has fallen. Their adventure ends here./i)
    ).toBeInTheDocument();
  });

  it('displays final stats from character', () => {
    render(
      <BrowserRouter>
        <DeathScreen character={mockCharacter} snapshot={null} />
      </BrowserRouter>
    );

    expect(screen.getByText('3')).toBeInTheDocument(); // Level
    expect(screen.getByText('4500')).toBeInTheDocument(); // XP
    expect(screen.getByText('150')).toBeInTheDocument(); // Gold
  });

  it('uses snapshot values when provided', () => {
    const snapshot = {
      hp: 0,
      max_hp: 25,
      xp: 5000,
      gold: 200,
      level: 4,
      inventory: [],
    };

    render(
      <BrowserRouter>
        <DeathScreen character={mockCharacter} snapshot={snapshot} />
      </BrowserRouter>
    );

    expect(screen.getByText('4')).toBeInTheDocument(); // Level from snapshot
    expect(screen.getByText('5000')).toBeInTheDocument(); // XP from snapshot
    expect(screen.getByText('200')).toBeInTheDocument(); // Gold from snapshot
  });

  it('navigates to create character page when button clicked', () => {
    render(
      <BrowserRouter>
        <DeathScreen character={mockCharacter} snapshot={null} />
      </BrowserRouter>
    );

    fireEvent.click(screen.getByText('Create New Character'));
    expect(mockNavigate).toHaveBeenCalledWith('/characters/new');
  });

  it('navigates to character list when button clicked', () => {
    render(
      <BrowserRouter>
        <DeathScreen character={mockCharacter} snapshot={null} />
      </BrowserRouter>
    );

    fireEvent.click(screen.getByText('Character List'));
    expect(mockNavigate).toHaveBeenCalledWith('/characters');
  });
});
