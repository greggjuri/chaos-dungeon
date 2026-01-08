/**
 * Tests for DiceRoll component.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DiceRoll } from './DiceRoll';
import { DiceRoll as DiceRollType } from '../../types';

describe('DiceRoll', () => {
  const baseRoll: DiceRollType = {
    type: 'attack',
    dice: 'd20',
    roll: 10,
    modifier: 3,
    total: 13,
    success: null,
  };

  it('renders roll type, value, modifier, and total', () => {
    render(<DiceRoll roll={baseRoll} />);

    // Shows type label (uppercase) when no attacker
    expect(screen.getByText(/ATTACK:/)).toBeInTheDocument();
    expect(screen.getByText(/d20\(10\)/)).toBeInTheDocument();
    expect(screen.getByText('+3')).toBeInTheDocument();
    expect(screen.getByText('13')).toBeInTheDocument();
  });

  it('shows negative modifier correctly', () => {
    const roll: DiceRollType = { ...baseRoll, modifier: -2, total: 8 };
    render(<DiceRoll roll={roll} />);

    expect(screen.getByText('-2')).toBeInTheDocument();
  });

  it('applies critical styling for natural 20', () => {
    const critRoll: DiceRollType = { ...baseRoll, roll: 20, total: 23 };
    const { container } = render(<DiceRoll roll={critRoll} />);

    // Check for gold/yellow styling on container
    expect(container.firstChild).toHaveClass('bg-yellow-900/30');
    expect(container.firstChild).toHaveClass('border-yellow-500/50');
  });

  it('applies fumble styling for natural 1', () => {
    const fumbleRoll: DiceRollType = { ...baseRoll, roll: 1, total: 4 };
    const { container } = render(<DiceRoll roll={fumbleRoll} />);

    // Check for red styling on container
    expect(container.firstChild).toHaveClass('bg-red-900/30');
    expect(container.firstChild).toHaveClass('border-red-500/50');
  });

  it('applies normal styling for regular rolls', () => {
    const { container } = render(<DiceRoll roll={baseRoll} />);

    expect(container.firstChild).toHaveClass('bg-gray-800/50');
  });

  it('shows HIT indicator when success is true', () => {
    const hitRoll: DiceRollType = { ...baseRoll, success: true };
    render(<DiceRoll roll={hitRoll} />);

    expect(screen.getByText('HIT')).toBeInTheDocument();
  });

  it('shows MISS indicator when success is false', () => {
    const missRoll: DiceRollType = { ...baseRoll, success: false };
    render(<DiceRoll roll={missRoll} />);

    expect(screen.getByText('MISS')).toBeInTheDocument();
  });

  it('shows no indicator when success is null', () => {
    render(<DiceRoll roll={baseRoll} />);

    expect(screen.queryByText('HIT')).not.toBeInTheDocument();
    expect(screen.queryByText('MISS')).not.toBeInTheDocument();
  });
});
