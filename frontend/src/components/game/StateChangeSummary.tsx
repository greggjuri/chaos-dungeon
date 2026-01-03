/**
 * State changes summary display component.
 */
import { StateChanges } from '../../types';

interface Props {
  changes: StateChanges;
}

/**
 * Display state changes (HP, Gold, XP) in a compact format.
 * Only shows non-zero values with appropriate colors.
 */
export function StateChangeSummary({ changes }: Props) {
  const items: React.ReactNode[] = [];

  // HP change: green for heal, red for damage
  if (changes.hp_delta !== 0) {
    const hpColor = changes.hp_delta > 0 ? 'text-green-400' : 'text-red-400';
    const hpSign = changes.hp_delta > 0 ? '+' : '';
    items.push(
      <span key="hp" className={`${hpColor} font-medium`}>
        {hpSign}
        {changes.hp_delta} HP
      </span>
    );
  }

  // Gold change: yellow for gain, gray for loss
  if (changes.gold_delta !== 0) {
    const goldColor =
      changes.gold_delta > 0 ? 'text-yellow-400' : 'text-gray-400';
    const goldSign = changes.gold_delta > 0 ? '+' : '';
    items.push(
      <span key="gold" className={`${goldColor} font-medium`}>
        {goldSign}
        {changes.gold_delta} Gold
      </span>
    );
  }

  // XP gain: blue
  if (changes.xp_delta !== 0) {
    const xpSign = changes.xp_delta > 0 ? '+' : '';
    items.push(
      <span key="xp" className="text-blue-400 font-medium">
        {xpSign}
        {changes.xp_delta} XP
      </span>
    );
  }

  // Location change
  if (changes.location) {
    items.push(
      <span key="location" className="text-purple-400">
        → {changes.location}
      </span>
    );
  }

  // Inventory additions
  if (changes.inventory_add.length > 0) {
    items.push(
      <span key="inv-add" className="text-emerald-400">
        +{changes.inventory_add.join(', ')}
      </span>
    );
  }

  // Inventory removals
  if (changes.inventory_remove.length > 0) {
    items.push(
      <span key="inv-remove" className="text-gray-500">
        -{changes.inventory_remove.join(', ')}
      </span>
    );
  }

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 text-sm mt-2 p-2 bg-gray-900/50 rounded">
      {items.map((item, idx) => (
        <span key={idx}>
          {item}
          {idx < items.length - 1 && (
            <span className="text-gray-600 ml-2">•</span>
          )}
        </span>
      ))}
    </div>
  );
}
