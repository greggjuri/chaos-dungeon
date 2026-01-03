/**
 * Death screen overlay component.
 */
import { useNavigate } from 'react-router-dom';
import { Character, CharacterSnapshot } from '../../types';

interface Props {
  character: Character;
  snapshot: CharacterSnapshot | null;
}

/**
 * Full-screen overlay displayed when character dies.
 * Shows final stats and navigation options.
 */
export function DeathScreen({ character, snapshot }: Props) {
  const navigate = useNavigate();

  // Use snapshot for final stats if available
  const level = snapshot?.level ?? character.level;
  const xp = snapshot?.xp ?? character.xp;
  const gold = snapshot?.gold ?? character.gold;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
      <div className="text-center px-6 max-w-md">
        {/* Death icon */}
        <div className="text-6xl mb-6">💀</div>

        {/* Death message */}
        <h1 className="text-3xl font-bold text-red-500 mb-2">YOU HAVE DIED</h1>
        <p className="text-gray-400 text-lg mb-8">
          {character.name} has fallen. Their adventure ends here.
        </p>

        {/* Final stats */}
        <div className="bg-gray-900/80 rounded-lg p-6 mb-8 border border-red-900/50">
          <h2 className="text-gray-400 text-sm uppercase tracking-wider mb-4">
            Final Record
          </h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-white">{level}</div>
              <div className="text-gray-500 text-sm">Level</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-400">{xp}</div>
              <div className="text-gray-500 text-sm">XP</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-400">{gold}</div>
              <div className="text-gray-500 text-sm">Gold</div>
            </div>
          </div>
        </div>

        {/* Navigation buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => navigate('/characters/new')}
            className="px-6 py-3 rounded-lg font-medium bg-amber-600 text-white hover:bg-amber-500 transition-colors"
          >
            Create New Character
          </button>
          <button
            onClick={() => navigate('/characters')}
            className="px-6 py-3 rounded-lg font-medium bg-gray-700 text-gray-200 hover:bg-gray-600 transition-colors"
          >
            Character List
          </button>
        </div>
      </div>
    </div>
  );
}
