/**
 * Tests for ChatMessage component.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ChatMessage } from './ChatMessage';
import { GameMessage } from '../../types';

describe('ChatMessage', () => {
  it('displays DM message with correct styling', () => {
    const message: GameMessage = {
      role: 'dm',
      content: 'You enter a dark cave.',
      timestamp: '2024-01-01T00:00:00Z',
    };

    const { container } = render(<ChatMessage message={message} />);

    expect(screen.getByText('Dungeon Master')).toBeInTheDocument();
    expect(screen.getByText('You enter a dark cave.')).toBeInTheDocument();
    expect(container.firstChild).toHaveClass('border-amber-600');
  });

  it('displays player message with correct styling', () => {
    const message: GameMessage = {
      role: 'player',
      content: 'I search the room.',
      timestamp: '2024-01-01T00:00:00Z',
    };

    const { container } = render(<ChatMessage message={message} />);

    expect(screen.getByText('You')).toBeInTheDocument();
    expect(screen.getByText('I search the room.')).toBeInTheDocument();
    expect(container.firstChild).toHaveClass('border-blue-600');
  });

  it('renders dice rolls when present', () => {
    const message: GameMessage = {
      role: 'dm',
      content: 'The goblin attacks!',
      timestamp: '2024-01-01T00:00:00Z',
      dice_rolls: [
        {
          type: 'attack',
          roll: 15,
          modifier: 3,
          total: 18,
          success: true,
        },
      ],
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText(/attack:/i)).toBeInTheDocument();
    expect(screen.getByText(/d20\(15\)/)).toBeInTheDocument();
  });

  it('renders multiple dice rolls', () => {
    const message: GameMessage = {
      role: 'dm',
      content: 'Combat round!',
      timestamp: '2024-01-01T00:00:00Z',
      dice_rolls: [
        { type: 'attack', roll: 12, modifier: 2, total: 14, success: true },
        { type: 'damage', roll: 6, modifier: 3, total: 9, success: null },
      ],
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText(/attack:/i)).toBeInTheDocument();
    expect(screen.getByText(/damage:/i)).toBeInTheDocument();
  });

  it('renders state changes when present', () => {
    const message: GameMessage = {
      role: 'dm',
      content: 'You find treasure!',
      timestamp: '2024-01-01T00:00:00Z',
      state_changes: {
        hp_delta: -5,
        gold_delta: 100,
        xp_delta: 50,
        location: null,
        inventory_add: [],
        inventory_remove: [],
        world_state: {},
      },
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText(/-5 HP/)).toBeInTheDocument();
    expect(screen.getByText(/\+100 Gold/)).toBeInTheDocument();
    expect(screen.getByText(/\+50 XP/)).toBeInTheDocument();
  });

  it('preserves whitespace in message content', () => {
    const message: GameMessage = {
      role: 'dm',
      content: 'Line 1\nLine 2\n  Indented',
      timestamp: '2024-01-01T00:00:00Z',
    };

    const { container } = render(<ChatMessage message={message} />);

    const contentDiv = container.querySelector('.whitespace-pre-wrap');
    expect(contentDiv).toBeInTheDocument();
  });

  it('does not render dice rolls section when empty', () => {
    const message: GameMessage = {
      role: 'dm',
      content: 'Simple message',
      timestamp: '2024-01-01T00:00:00Z',
      dice_rolls: [],
    };

    render(<ChatMessage message={message} />);

    // Should not have attack/damage labels
    expect(screen.queryByText(/attack:/i)).not.toBeInTheDocument();
  });
});
