/**
 * Combat status panel component.
 */
import { CombatEnemy } from '../../types';

interface Props {
  enemies: CombatEnemy[];
  combatActive: boolean;
}

/**
 * Display combat status with enemy list.
 * Only shows when combat is active and there are living enemies.
 */
export function CombatStatus({ enemies, combatActive }: Props) {
  // Filter to living enemies only
  const livingEnemies = enemies.filter((e) => e.hp > 0);

  // Hide if not in combat or no living enemies
  if (!combatActive || livingEnemies.length === 0) {
    return null;
  }

  return (
    <div className="bg-red-900/30 border border-red-700/50 mx-4 mb-2 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-red-400 font-bold text-sm uppercase tracking-wider">
          ⚔️ In Combat
        </span>
      </div>

      <div className="space-y-1">
        {livingEnemies.map((enemy, idx) => {
          const hpPercentage = (enemy.hp / enemy.max_hp) * 100;
          const hpColor =
            hpPercentage > 50
              ? 'text-green-400'
              : hpPercentage > 25
                ? 'text-yellow-400'
                : 'text-red-400';

          return (
            <div
              key={enemy.id || idx}
              className="flex items-center justify-between text-sm bg-gray-800/50 px-2 py-1 rounded"
            >
              <span className="text-gray-200">{enemy.name}</span>
              <div className="flex items-center gap-3">
                <span className={hpColor}>
                  HP: {enemy.hp}/{enemy.max_hp}
                </span>
                <span className="text-gray-400">AC: {enemy.ac}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
