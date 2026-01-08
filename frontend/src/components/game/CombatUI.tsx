/**
 * Turn-based combat UI component.
 *
 * Displays enemy status, action buttons, and combat log.
 * Player selects targets and actions through this interface.
 */
import { useState, useCallback } from 'react';
import { CombatAction, CombatResponse } from '../../types';
import { ActionBar } from './ActionBar';
import { CombatLog } from './CombatLog';
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
 * Main combat interface showing enemies, player status,
 * action buttons, and combat log.
 */
export function CombatUI({ combat, onAction, isLoading }: CombatUIProps) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);

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
    setSelectedTarget((prev) => (prev === enemyId ? null : enemyId));
  }, []);

  // Get HP color based on percentage
  const hpPercent = (combat.your_hp / combat.your_max_hp) * 100;
  const hpColor =
    hpPercent > 50 ? 'text-green-400' : hpPercent > 25 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="bg-gray-900 border-t border-red-800 p-3 mx-2 mb-2">
      {/* Compact combat header with HP */}
      <div className="flex items-center justify-between mb-2">
        <div className="text-red-500 font-bold text-sm">⚔️ COMBAT - Round {combat.round}</div>
        <div className="text-sm">
          <span className="text-gray-400">HP: </span>
          <span className={`font-bold ${hpColor}`}>
            {combat.your_hp}/{combat.your_max_hp}
          </span>
        </div>
      </div>

      {/* Enemy list - more compact */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-1.5 mb-2">
        {combat.enemies.map((enemy) => (
          <EnemyCard
            key={enemy.id || enemy.name}
            enemy={enemy}
            isSelected={effectiveTarget === enemy.id}
            onSelect={() => enemy.id && handleEnemySelect(enemy.id)}
            selectable={enemy.id ? combat.valid_targets.includes(enemy.id) : false}
          />
        ))}
      </div>

      {/* Action buttons */}
      <ActionBar
        availableActions={combat.available_actions}
        selectedTarget={effectiveTarget}
        hasValidTarget={combat.valid_targets.length > 0}
        onAction={handleAction}
        disabled={isLoading}
      />

      {/* Combat log - collapsible, only show last 3 */}
      {combat.combat_log.length > 0 && <CombatLog entries={combat.combat_log.slice(-3)} />}
    </div>
  );
}
