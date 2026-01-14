/**
 * Tests for CharacterStatus component.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CharacterStatus } from './CharacterStatus';
import { Character } from '../../types';

describe('CharacterStatus', () => {
  const mockCharacter: Character = {
    character_id: 'char-1',
    user_id: 'user-1',
    name: 'Thorin',
    character_class: 'fighter',
    level: 3,
    xp: 4500,
    hp: 20,
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
    inventory: [{ name: 'Sword', quantity: 1, weight: 5, item_type: 'weapon' }],
    created_at: '2024-01-01T00:00:00Z',
  };

  it('displays character name and class', () => {
    render(<CharacterStatus character={mockCharacter} snapshot={null} />);

    expect(screen.getByText('Thorin')).toBeInTheDocument();
    expect(screen.getByText(/Fighter/)).toBeInTheDocument();
    expect(screen.getByText(/Level 3/)).toBeInTheDocument();
  });

  it('displays HP value', () => {
    render(<CharacterStatus character={mockCharacter} snapshot={null} />);

    expect(screen.getByText('20/25')).toBeInTheDocument();
  });

  it('displays XP value', () => {
    render(<CharacterStatus character={mockCharacter} snapshot={null} />);

    expect(screen.getByText('4500')).toBeInTheDocument();
  });

  it('displays gold value', () => {
    render(<CharacterStatus character={mockCharacter} snapshot={null} />);

    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('uses snapshot values when provided', () => {
    const snapshot = {
      hp: 15,
      max_hp: 25,
      xp: 5000,
      gold: 200,
      level: 4,
      inventory: ['Sword', 'Shield'],
    };

    render(<CharacterStatus character={mockCharacter} snapshot={snapshot} />);

    expect(screen.getByText('15/25')).toBeInTheDocument();
    expect(screen.getByText('5000')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText(/Level 4/)).toBeInTheDocument();
  });

  it('shows green HP bar when HP > 50%', () => {
    const { container } = render(
      <CharacterStatus character={mockCharacter} snapshot={null} />
    );

    // HP is 20/25 = 80%, should be green
    const hpBar = container.querySelector('.bg-green-500');
    expect(hpBar).toBeInTheDocument();
  });

  it('shows yellow HP bar when HP is 25-50%', () => {
    const snapshot = {
      hp: 10,
      max_hp: 25,
      xp: 4500,
      gold: 150,
      level: 3,
      inventory: [],
    };

    const { container } = render(
      <CharacterStatus character={mockCharacter} snapshot={snapshot} />
    );

    // HP is 10/25 = 40%, should be yellow
    const hpBar = container.querySelector('.bg-yellow-500');
    expect(hpBar).toBeInTheDocument();
  });

  it('shows red HP bar when HP < 25%', () => {
    const snapshot = {
      hp: 5,
      max_hp: 25,
      xp: 4500,
      gold: 150,
      level: 3,
      inventory: [],
    };

    const { container } = render(
      <CharacterStatus character={mockCharacter} snapshot={snapshot} />
    );

    // HP is 5/25 = 20%, should be red
    const hpBar = container.querySelector('.bg-red-500');
    expect(hpBar).toBeInTheDocument();
  });
});
