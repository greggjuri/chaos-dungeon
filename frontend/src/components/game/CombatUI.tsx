/**
 * Turn-based combat UI component.
 *
 * Minimal compact interface showing enemies and action buttons.
 * Player selects targets and actions through this interface.
 */
import { useState, useCallback, useEffect } from 'react';
import { CombatAction, CombatResponse } from '../../types';
import { ActionBar } from './ActionBar';
import { EnemyCard } from './EnemyCard';

interface CombatUIProps {
  /** Combat state from server */
  combat: CombatResponse;
  /** Callback when player takes an action */
  onAction: (action: CombatAction) => void;
  /** Whether an action is currently being processed */
  isLoading: boolean;
}

/**
 * Compact combat interface showing enemies and action buttons.
 */
export function CombatUI({ combat, onAction, isLoading }: CombatUIProps) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);

  // Debug: log combat data
  useEffect(() => {
    console.log('[CombatUI] combat data:', {
      enemies: combat.enemies.map(e => ({ id: e.id, name: e.name, hp: e.hp })),
      valid_targets: combat.valid_targets,
      round: combat.round
    });
  }, [combat]);

  // Auto-select first valid target if none selected
  const effectiveTarget = selectedTarget && combat.valid_targets.includes(selectedTarget)
    ? selectedTarget
    : combat.valid_targets[0] || null;

  const handleAction = useCallback(
    (action: CombatAction) => {
      // For attack actions, ensure we have a target
      if (action.action_type === 'attack' && !action.target_id) {
        action = { ...action, target_id: effectiveTarget || undefined };
      }
      onAction(action);
    },
    [effectiveTarget, onAction]
  );

  const handleEnemySelect = useCallback((enemyId: string) => {
    console.log('[CombatUI] handleEnemySelect called with:', enemyId);
    setSelectedTarget((prev) => {
      const newTarget = prev === enemyId ? null : enemyId;
      console.log('[CombatUI] selectedTarget changing from', prev, 'to', newTarget);
      return newTarget;
    });
  }, []);

  // Get HP color based on percentage
  const hpPercent = (combat.your_hp / combat.your_max_hp) * 100;
  const hpColor =
    hpPercent > 50 ? 'text-green-400' : hpPercent > 25 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="bg-gray-900/95 border-t border-red-800/50 px-2 py-1.5">
      {/* Single row: Round, Enemies, HP, Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Round indicator */}
        <span className="text-red-500 font-bold text-xs whitespace-nowrap">⚔️ R{combat.round}</span>

        {/* Enemy pills - compact inline */}
        <div className="flex gap-1 flex-wrap flex-1">
          {combat.enemies.map((enemy) => {
            const isSelectable = enemy.id ? combat.valid_targets.includes(enemy.id) : false;
            console.log('[CombatUI] rendering enemy', enemy.name, 'id:', enemy.id, 'selectable:', isSelectable);
            return (
              <EnemyCard
                key={enemy.id || enemy.name}
                enemy={enemy}
                isSelected={effectiveTarget === enemy.id}
                onSelect={() => {
                  console.log('[CombatUI] onSelect callback triggered for', enemy.name, enemy.id);
                  if (enemy.id) {
                    handleEnemySelect(enemy.id);
                  }
                }}
                selectable={isSelectable}
              />
            );
          })}
        </div>

        {/* HP */}
        <span className={`text-xs font-bold ${hpColor} whitespace-nowrap`}>
          {combat.your_hp}/{combat.your_max_hp} HP
        </span>

        {/* Compact action buttons */}
        <ActionBar
          availableActions={combat.available_actions}
          selectedTarget={effectiveTarget}
          hasValidTarget={combat.valid_targets.length > 0}
          onAction={handleAction}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}
