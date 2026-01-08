/**
 * Combat action bar component.
 *
 * Displays action buttons for the player during combat:
 * Attack, Defend, Flee, and Use Item.
 */
import { CombatAction, CombatActionType } from '../../types';

interface ActionBarProps {
  /** Actions available to the player */
  availableActions: CombatActionType[];
  /** Currently selected target ID */
  selectedTarget: string | null;
  /** Whether there are valid targets */
  hasValidTarget: boolean;
  /** Callback when an action is taken */
  onAction: (action: CombatAction) => void;
  /** Whether actions are disabled (loading) */
  disabled: boolean;
}

const ACTION_CONFIG: Record<
  CombatActionType,
  { label: string; emoji: string; color: string; hoverColor: string }
> = {
  attack: {
    label: 'Attack',
    emoji: '⚔️',
    color: 'bg-red-700',
    hoverColor: 'hover:bg-red-600',
  },
  defend: {
    label: 'Defend',
    emoji: '🛡️',
    color: 'bg-blue-700',
    hoverColor: 'hover:bg-blue-600',
  },
  flee: {
    label: 'Flee',
    emoji: '🏃',
    color: 'bg-yellow-700',
    hoverColor: 'hover:bg-yellow-600',
  },
  use_item: {
    label: 'Item',
    emoji: '🧪',
    color: 'bg-green-700',
    hoverColor: 'hover:bg-green-600',
  },
};

/**
 * Row of combat action buttons.
 */
export function ActionBar({
  availableActions,
  selectedTarget,
  hasValidTarget,
  onAction,
  disabled,
}: ActionBarProps) {
  const handleClick = (actionType: CombatActionType) => {
    const action: CombatAction = { action_type: actionType };

    // Add target for attack action
    if (actionType === 'attack' && selectedTarget) {
      action.target_id = selectedTarget;
    }

    onAction(action);
  };

  return (
    <div className="flex flex-wrap gap-2 justify-center">
      {availableActions.map((actionType) => {
        const config = ACTION_CONFIG[actionType];
        // Attack requires a target
        const needsTarget = actionType === 'attack';
        const isDisabled = disabled || (needsTarget && !hasValidTarget);

        return (
          <button
            key={actionType}
            onClick={() => handleClick(actionType)}
            disabled={isDisabled}
            className={`
              px-4 py-2 rounded font-bold text-white transition-colors
              ${config.color} ${config.hoverColor}
              disabled:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50
              flex items-center gap-2
            `}
            title={
              needsTarget && !hasValidTarget
                ? 'Select a target first'
                : `${config.label} action`
            }
          >
            <span>{config.emoji}</span>
            <span>{config.label}</span>
          </button>
        );
      })}
    </div>
  );
}
