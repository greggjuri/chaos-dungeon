/**
 * Enemy card component for combat UI.
 *
 * Displays an enemy's name, HP bar, and selection state.
 */
import { CombatEnemy } from '../../types';

interface EnemyCardProps {
  /** Enemy data */
  enemy: CombatEnemy;
  /** Whether this enemy is currently selected */
  isSelected: boolean;
  /** Callback when enemy is clicked */
  onSelect: () => void;
  /** Whether this enemy can be selected */
  selectable: boolean;
}

/**
 * Individual enemy card showing name and HP.
 */
export function EnemyCard({ enemy, isSelected, onSelect, selectable }: EnemyCardProps) {
  const isDead = enemy.hp <= 0;
  const hpPercent = enemy.max_hp > 0 ? (enemy.hp / enemy.max_hp) * 100 : 0;

  // HP bar color based on health
  const getHpBarColor = () => {
    if (hpPercent > 50) return 'bg-green-500';
    if (hpPercent > 25) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <button
      onClick={onSelect}
      disabled={!selectable || isDead}
      className={`
        p-3 rounded border transition-all text-left w-full
        ${isDead ? 'opacity-40 cursor-not-allowed border-gray-700 bg-gray-900' : ''}
        ${isSelected && !isDead ? 'border-red-500 bg-red-900/30 ring-2 ring-red-500' : ''}
        ${!isSelected && !isDead && selectable ? 'border-gray-600 bg-gray-800 hover:border-red-400 hover:bg-gray-700' : ''}
        ${!selectable && !isDead ? 'border-gray-700 bg-gray-800 cursor-not-allowed' : ''}
      `}
    >
      {/* Enemy name */}
      <div className={`font-bold mb-2 ${isDead ? 'line-through text-gray-500' : 'text-white'}`}>
        {enemy.name}
        {isDead && <span className="text-red-500 ml-2">💀</span>}
      </div>

      {/* HP bar */}
      <div className="h-2 bg-gray-700 rounded overflow-hidden mb-1">
        <div
          className={`h-full transition-all ${getHpBarColor()}`}
          style={{ width: `${Math.max(0, hpPercent)}%` }}
        />
      </div>

      {/* HP text */}
      <div className="text-xs text-gray-400">
        HP: {enemy.hp}/{enemy.max_hp}
        {enemy.ac && <span className="ml-2">AC: {enemy.ac}</span>}
      </div>
    </button>
  );
}
