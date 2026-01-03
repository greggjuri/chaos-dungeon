/**
 * Single dice roll display component.
 */
import { DiceRoll as DiceRollType } from '../../types';

interface Props {
  roll: DiceRollType;
}

/**
 * Display a single dice roll with type, roll value, modifier, and total.
 * Highlights critical hits (20) in gold and fumbles (1) in red.
 */
export function DiceRoll({ roll }: Props) {
  const isCritical = roll.roll === 20;
  const isFumble = roll.roll === 1;

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

  // Success/fail indicator for attacks
  const successIndicator =
    roll.success === true ? (
      <span className="ml-2 text-green-400 text-xs">HIT</span>
    ) : roll.success === false ? (
      <span className="ml-2 text-red-400 text-xs">MISS</span>
    ) : null;

  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded border ${containerClasses}`}
    >
      <span className="text-gray-400 text-xs uppercase">{roll.type}:</span>
      <span className={`text-sm ${rollValueClasses}`}>d20({roll.roll})</span>
      <span className="text-gray-400 text-sm">{modifierStr}</span>
      <span className="text-gray-400 text-sm">=</span>
      <span className="text-white font-semibold text-sm">{roll.total}</span>
      {successIndicator}
    </div>
  );
}
