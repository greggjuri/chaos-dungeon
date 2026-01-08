/**
 * Death screen component displayed inline at the bottom of chat.
 */
import { useNavigate } from 'react-router-dom';
import { Character, CharacterSnapshot } from '../../types';

interface Props {
  character: Character;
  snapshot: CharacterSnapshot | null;
}

/**
 * Inline death notice displayed at the bottom of chat when character dies.
 * Shows final stats and navigation options without blocking the chat history.
 */
export function DeathScreen({ character, snapshot }: Props) {
  const navigate = useNavigate();

  // Use snapshot for final stats if available
  const level = snapshot?.level ?? character.level;
  const xp = snapshot?.xp ?? character.xp;
  const gold = snapshot?.gold ?? character.gold;

  return (
    <div className="border-t border-red-900/50 bg-gradient-to-t from-red-950/30 to-gray-900 p-4">
      <div className="max-w-2xl mx-auto">
        {/* Compact death header */}
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">💀</span>
          <div>
            <h1 className="text-xl font-bold text-red-500">YOU HAVE DIED</h1>
            <p className="text-gray-400 text-sm">
              {character.name} has fallen. Their adventure ends here.
            </p>
          </div>
        </div>

        {/* Final stats - compact inline */}
        <div className="flex items-center gap-6 mb-4 text-sm">
          <span className="text-gray-500">Final Record:</span>
          <span>
            <span className="text-white font-medium">{level}</span>
            <span className="text-gray-500 ml-1">Level</span>
          </span>
          <span>
            <span className="text-blue-400 font-medium">{xp}</span>
            <span className="text-gray-500 ml-1">XP</span>
          </span>
          <span>
            <span className="text-yellow-400 font-medium">{gold}</span>
            <span className="text-gray-500 ml-1">Gold</span>
          </span>
        </div>

        {/* Navigation buttons - compact row */}
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/characters/new')}
            className="px-4 py-2 rounded-lg font-medium text-sm bg-amber-600 text-white hover:bg-amber-500 transition-colors"
          >
            Create New Character
          </button>
          <button
            onClick={() => navigate('/characters')}
            className="px-4 py-2 rounded-lg font-medium text-sm bg-gray-700 text-gray-200 hover:bg-gray-600 transition-colors"
          >
            Character List
          </button>
        </div>
      </div>
    </div>
  );
}
