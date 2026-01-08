/**
 * Single dice roll display component.
 */
import { DiceRoll as DiceRollType } from '../../types';

interface Props {
  roll: DiceRollType;
}

/**
 * Display a single dice roll with type, roll value, modifier, and total.
 * Shows attacker → target for combat rolls.
 * Only shows HIT/MISS for attack rolls (not damage).
 */
export function DiceRoll({ roll }: Props) {
  const isAttackRoll = roll.type === 'attack';
  const isCritical = isAttackRoll && roll.roll === 20;
  const isFumble = isAttackRoll && roll.roll === 1;

  // Determine styling based on roll
  const containerClasses = isCritical
    ? 'bg-yellow-900/30 border-yellow-500/50'
    : isFumble
      ? 'bg-red-900/30 border-red-500/50'
      : 'bg-gray-800/50 border-gray-600/50';

  const rollValueClasses = isCritical
    ? 'text-yellow-400 font-bold'
    : isFumble
      ? 'text-red-400 font-bold'
      : 'text-gray-200';

  // Format modifier with sign
  const modifierStr =
    roll.modifier >= 0 ? `+${roll.modifier}` : `${roll.modifier}`;

  // Only show HIT/MISS for attack rolls
  const successIndicator =
    isAttackRoll && roll.success === true ? (
      <span className="ml-1 text-green-400 text-xs">HIT</span>
    ) : isAttackRoll && roll.success === false ? (
      <span className="ml-1 text-red-400 text-xs">MISS</span>
    ) : null;

  // Use the dice type from the roll (e.g., "d20", "d8", "d6")
  const diceType = roll.dice || 'd20';

  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded border ${containerClasses}`}
    >
      {/* Attacker name */}
      <span className="text-gray-300 text-xs">
        {roll.attacker || roll.type.toUpperCase()}:
      </span>
      <span className={`text-sm ${rollValueClasses}`}>{diceType}({roll.roll})</span>
      <span className="text-gray-400 text-sm">{modifierStr}</span>
      <span className="text-gray-400 text-sm">=</span>
      <span className="text-white font-semibold text-sm">{roll.total}</span>
      {successIndicator}
    </div>
  );
}
