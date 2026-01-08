/**
 * Enemy card component for combat UI.
 *
 * Displays an enemy as a compact clickable pill with name and HP.
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
 * Compact enemy pill showing name and HP.
 * Click to select as target.
 */
export function EnemyCard({ enemy, isSelected, onSelect, selectable }: EnemyCardProps) {
  const isDead = enemy.hp <= 0;
  const hpPercent = enemy.max_hp > 0 ? (enemy.hp / enemy.max_hp) * 100 : 0;

  // HP text color based on health
  const getHpColor = () => {
    if (hpPercent > 50) return 'text-green-400';
    if (hpPercent > 25) return 'text-yellow-400';
    return 'text-red-400';
  };

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (selectable && !isDead) {
      onSelect();
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={!selectable || isDead}
      className={`
        inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs
        transition-all select-none
        ${isDead
          ? 'opacity-40 cursor-not-allowed bg-gray-800 border border-gray-700'
          : isSelected
            ? 'bg-red-900/50 border-2 border-red-500 ring-1 ring-red-500/50 cursor-pointer'
            : selectable
              ? 'bg-gray-800 border border-gray-600 hover:border-red-400 hover:bg-gray-700 cursor-pointer active:bg-gray-600'
              : 'bg-gray-800 border border-gray-700 cursor-not-allowed'
        }
      `}
    >
      {/* Enemy name */}
      <span className={`font-medium ${isDead ? 'line-through text-gray-500' : 'text-white'}`}>
        {enemy.name}
        {isDead && <span className="ml-0.5">💀</span>}
      </span>

      {/* HP */}
      {!isDead && (
        <span className={`${getHpColor()} font-mono`}>
          {enemy.hp}/{enemy.max_hp}
        </span>
      )}

      {/* Selection indicator */}
      {isSelected && !isDead && (
        <span className="text-red-400">⚔</span>
      )}
    </button>
  );
}
