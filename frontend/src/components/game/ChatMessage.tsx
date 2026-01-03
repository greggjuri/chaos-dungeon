/**
 * Chat message bubble component.
 */
import { GameMessage } from '../../types';
import { DiceRoll } from './DiceRoll';
import { StateChangeSummary } from './StateChangeSummary';

interface Props {
  message: GameMessage;
}

/**
 * Display a single chat message with optional dice rolls and state changes.
 * DM messages have amber styling, player messages have a distinct style.
 */
export function ChatMessage({ message }: Props) {
  const isDM = message.role === 'dm';

  const containerClasses = isDM
    ? 'border-l-4 border-amber-600 bg-gray-800/50 pl-4 pr-3 py-3'
    : 'border-l-4 border-blue-600 bg-blue-900/20 pl-4 pr-3 py-3';

  const roleLabel = isDM ? 'Dungeon Master' : 'You';
  const roleLabelClasses = isDM ? 'text-amber-400' : 'text-blue-400';

  return (
    <div className={`rounded-r ${containerClasses}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-sm font-semibold ${roleLabelClasses}`}>
          {roleLabel}
        </span>
      </div>

      <div className="text-gray-200 whitespace-pre-wrap break-words">
        {message.content}
      </div>

      {message.dice_rolls && message.dice_rolls.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {message.dice_rolls.map((roll, idx) => (
            <DiceRoll key={idx} roll={roll} />
          ))}
        </div>
      )}

      {message.state_changes && (
        <StateChangeSummary changes={message.state_changes} />
      )}
    </div>
  );
}
