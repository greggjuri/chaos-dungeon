/**
 * Inventory panel component - displays character's items grouped by type.
 */
import { Item } from '../../types';

interface InventoryPanelProps {
  items: Item[];
  onUseItem?: (itemId: string) => void;
  inCombat?: boolean;
}

/**
 * Get the color class for an item type.
 */
function getItemTypeColor(itemType: string): string {
  switch (itemType) {
    case 'weapon':
      return 'text-red-400';
    case 'armor':
      return 'text-blue-400';
    case 'consumable':
      return 'text-green-400';
    case 'quest':
      return 'text-purple-400';
    default:
      return 'text-gray-400';
  }
}

/**
 * Inventory panel showing items grouped by type.
 * Shows "Use" button for consumables during combat.
 */
export function InventoryPanel({ items, onUseItem, inCombat }: InventoryPanelProps) {
  if (!items || items.length === 0) {
    return (
      <div className="p-4 text-gray-500 italic text-sm">
        Your pack is empty.
      </div>
    );
  }

  // Group items by type
  const equipment = items.filter(i => i.item_type === 'weapon' || i.item_type === 'armor');
  const consumables = items.filter(i => i.item_type === 'consumable');
  const questItems = items.filter(i => i.item_type === 'quest');
  const other = items.filter(i => !['weapon', 'armor', 'consumable', 'quest'].includes(i.item_type));

  return (
    <div className="p-3 space-y-3 text-sm">
      {/* Equipment */}
      {equipment.length > 0 && (
        <div>
          <h4 className="font-bold text-amber-400 mb-1 text-xs uppercase tracking-wider">Equipment</h4>
          <div className="space-y-0.5">
            {equipment.map((item, idx) => (
              <div key={item.item_id || idx} className="flex justify-between items-center">
                <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
                {item.quantity > 1 && (
                  <span className="text-gray-500 text-xs">x{item.quantity}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consumables */}
      {consumables.length > 0 && (
        <div>
          <h4 className="font-bold text-green-400 mb-1 text-xs uppercase tracking-wider">Consumables</h4>
          <div className="space-y-0.5">
            {consumables.map((item, idx) => (
              <div key={item.item_id || idx} className="flex justify-between items-center">
                <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 text-xs">x{item.quantity}</span>
                  {inCombat && onUseItem && item.item_id && (
                    <button
                      onClick={() => onUseItem(item.item_id!)}
                      className="px-2 py-0.5 text-xs bg-green-600 hover:bg-green-500 rounded text-white"
                    >
                      Use
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quest Items */}
      {questItems.length > 0 && (
        <div>
          <h4 className="font-bold text-purple-400 mb-1 text-xs uppercase tracking-wider">Quest Items</h4>
          <div className="space-y-0.5">
            {questItems.map((item, idx) => (
              <div key={item.item_id || idx} className="flex justify-between items-center">
                <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
                {item.quantity > 1 && (
                  <span className="text-gray-500 text-xs">x{item.quantity}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Other */}
      {other.length > 0 && (
        <div>
          <h4 className="font-bold text-gray-400 mb-1 text-xs uppercase tracking-wider">Other</h4>
          <div className="space-y-0.5">
            {other.map((item, idx) => (
              <div key={item.item_id || idx} className="flex justify-between items-center">
                <span className={getItemTypeColor(item.item_type)}>{item.name}</span>
                {item.quantity > 1 && (
                  <span className="text-gray-500 text-xs">x{item.quantity}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
