/**
 * Character sheet panel showing full character details.
 * Displays name, class, level, stats, and ability scores.
 */
import { Character, CharacterSnapshot, CharacterClass } from '../../types';

interface CharacterSheetProps {
  character: Character;
  snapshot: CharacterSnapshot | null;
}

const CLASS_DISPLAY: Record<CharacterClass, string> = {
  fighter: 'Fighter',
  thief: 'Thief',
  magic_user: 'Magic User',
  cleric: 'Cleric',
};

/**
 * Get HP bar color based on percentage.
 */
function getHpColor(current: number, max: number): string {
  const percentage = (current / max) * 100;
  if (percentage > 50) return 'bg-green-500';
  if (percentage > 25) return 'bg-yellow-500';
  return 'bg-red-500';
}

/**
 * Get ability score modifier display.
 */
function getAbilityModifier(score: number): string {
  if (score >= 16) return '+2';
  if (score >= 13) return '+1';
  if (score >= 9) return '0';
  if (score >= 6) return '-1';
  return '-2';
}

/**
 * Character sheet panel with full details including ability scores.
 */
export function CharacterSheet({ character, snapshot }: CharacterSheetProps) {
  // Use snapshot values if available, fall back to character
  const hp = snapshot?.hp ?? character.hp;
  const maxHp = snapshot?.max_hp ?? character.max_hp;
  const xp = snapshot?.xp ?? character.xp;
  const gold = snapshot?.gold ?? character.gold;
  const level = snapshot?.level ?? character.level;
  const abilities = character.abilities;

  const hpPercentage = Math.max(0, Math.min(100, (hp / maxHp) * 100));
  const hpColor = getHpColor(hp, maxHp);

  return (
    <div className="p-4 space-y-4">
      {/* Header - Name and Class */}
      <div className="text-center border-b border-gray-700 pb-3">
        <h2 className="text-xl font-bold text-white">{character.name}</h2>
        <p className="text-gray-400">
          Level {level} {CLASS_DISPLAY[character.character_class]}
        </p>
      </div>

      {/* Vital Stats */}
      <div className="space-y-3">
        {/* HP with bar */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Hit Points</span>
            <span
              className={
                hp <= maxHp * 0.25
                  ? 'text-red-400'
                  : hp <= maxHp * 0.5
                    ? 'text-yellow-400'
                    : 'text-green-400'
              }
            >
              {hp} / {maxHp}
            </span>
          </div>
          <div className="w-full h-3 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${hpColor} transition-all duration-300`}
              style={{ width: `${hpPercentage}%` }}
            />
          </div>
        </div>

        {/* XP and Gold row */}
        <div className="flex justify-between">
          <div>
            <span className="text-gray-400 text-sm">Experience</span>
            <p className="text-blue-400 font-medium">{xp.toLocaleString()}</p>
          </div>
          <div className="text-right">
            <span className="text-gray-400 text-sm">Gold</span>
            <p className="text-yellow-400 font-medium">{gold.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Ability Scores */}
      <div className="border-t border-gray-700 pt-3">
        <h3 className="text-amber-400 font-bold text-xs uppercase tracking-wider mb-2">
          Ability Scores
        </h3>
        <div className="grid grid-cols-3 gap-2">
          {/* Row 1: STR, INT, WIS */}
          <AbilityScore label="STR" value={abilities.strength} />
          <AbilityScore label="INT" value={abilities.intelligence} />
          <AbilityScore label="WIS" value={abilities.wisdom} />
          {/* Row 2: DEX, CON, CHA */}
          <AbilityScore label="DEX" value={abilities.dexterity} />
          <AbilityScore label="CON" value={abilities.constitution} />
          <AbilityScore label="CHA" value={abilities.charisma} />
        </div>
      </div>
    </div>
  );
}

/**
 * Individual ability score display with modifier.
 */
function AbilityScore({ label, value }: { label: string; value: number }) {
  const modifier = getAbilityModifier(value);
  const modColor =
    modifier.startsWith('+') ? 'text-green-400' : modifier === '0' ? 'text-gray-400' : 'text-red-400';

  return (
    <div className="bg-gray-800 rounded p-2 text-center">
      <div className="text-gray-500 text-xs">{label}</div>
      <div className="text-white font-bold text-lg">{value}</div>
      <div className={`text-xs ${modColor}`}>{modifier}</div>
    </div>
  );
}
