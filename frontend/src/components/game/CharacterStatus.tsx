/**
 * Character status bar component.
 */
import { Package, User } from 'lucide-react';
import { Character, CharacterSnapshot, CharacterClass } from '../../types';

interface Props {
  character: Character;
  snapshot: CharacterSnapshot | null;
  onInventoryClick?: () => void;
  onCharacterClick?: () => void;
}

const CLASS_DISPLAY: Record<CharacterClass, string> = {
  fighter: 'Fighter',
  thief: 'Thief',
  magic_user: 'Magic User',
  cleric: 'Cleric',
};

/**
 * Get HP bar color based on percentage.
 * > 50%: green, 25-50%: yellow, < 25%: red
 */
function getHpColor(current: number, max: number): string {
  const percentage = (current / max) * 100;
  if (percentage > 50) return 'bg-green-500';
  if (percentage > 25) return 'bg-yellow-500';
  return 'bg-red-500';
}

/**
 * Top status bar showing character info, HP, XP, and Gold.
 * Uses snapshot values when available (updated after actions).
 * Includes icon buttons for inventory and character sheet panels.
 */
export function CharacterStatus({
  character,
  snapshot,
  onInventoryClick,
  onCharacterClick,
}: Props) {
  // Use snapshot values if available, fall back to character
  const hp = snapshot?.hp ?? character.hp;
  const maxHp = snapshot?.max_hp ?? character.max_hp;
  const xp = snapshot?.xp ?? character.xp;
  const gold = snapshot?.gold ?? character.gold;
  const level = snapshot?.level ?? character.level;

  const hpPercentage = Math.max(0, Math.min(100, (hp / maxHp) * 100));
  const hpColor = getHpColor(hp, maxHp);

  return (
    <div className="bg-gray-800 border-b border-gray-700 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Character info */}
        <div className="flex items-center gap-3">
          <span className="font-bold text-white">{character.name}</span>
          <span className="text-gray-400 text-sm">
            {CLASS_DISPLAY[character.character_class]} • Level {level}
          </span>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-sm">
          {/* HP with bar */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400">HP:</span>
            <div className="w-24 h-3 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${hpColor} transition-all duration-300`}
                style={{ width: `${hpPercentage}%` }}
              />
            </div>
            <span
              className={
                hp <= maxHp * 0.25
                  ? 'text-red-400'
                  : hp <= maxHp * 0.5
                    ? 'text-yellow-400'
                    : 'text-green-400'
              }
            >
              {hp}/{maxHp}
            </span>
          </div>

          {/* XP */}
          <div className="flex items-center gap-1">
            <span className="text-gray-400">XP:</span>
            <span className="text-blue-400">{xp}</span>
          </div>

          {/* Gold */}
          <div className="flex items-center gap-1">
            <span className="text-gray-400">Gold:</span>
            <span className="text-yellow-400">{gold}</span>
          </div>

          {/* Panel icons */}
          <div className="flex items-center gap-1 ml-2 border-l border-gray-600 pl-2">
            <button
              onClick={onInventoryClick}
              className="text-gray-500 hover:text-gray-300 transition-colors p-1"
              title="Inventory (I)"
              aria-label="Open inventory"
            >
              <Package size={18} />
            </button>
            <button
              onClick={onCharacterClick}
              className="text-gray-500 hover:text-gray-300 transition-colors p-1"
              title="Character (C)"
              aria-label="Open character sheet"
            >
              <User size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
