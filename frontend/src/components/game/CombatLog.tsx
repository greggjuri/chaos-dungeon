/**
 * Combat log component.
 *
 * Displays recent combat actions and their results.
 */
import { useRef, useEffect } from 'react';
import { CombatLogEntry } from '../../types';

interface CombatLogProps {
  /** Combat log entries to display */
  entries: CombatLogEntry[];
}

/**
 * Scrollable combat log showing recent actions.
 */
export function CombatLog({ entries }: CombatLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  if (entries.length === 0) {
    return null;
  }

  return (
    <div
      ref={scrollRef}
      className="mt-4 max-h-32 overflow-y-auto bg-gray-800 rounded p-2 text-sm"
    >
      <div className="text-gray-500 text-xs mb-2 border-b border-gray-700 pb-1">
        Combat Log
      </div>
      {entries.map((entry, i) => (
        <CombatLogEntryRow key={`${entry.round}-${i}`} entry={entry} />
      ))}
    </div>
  );
}

interface CombatLogEntryRowProps {
  entry: CombatLogEntry;
}

function CombatLogEntryRow({ entry }: CombatLogEntryRowProps) {
  const isPlayer = entry.actor === 'player';
  const actorColor = isPlayer ? 'text-blue-400' : 'text-red-400';

  // Format the result message
  const getMessage = () => {
    const actor = isPlayer ? 'You' : entry.actor;

    switch (entry.result) {
      case 'hit':
        return (
          <>
            <span className={actorColor}>{actor}</span>
            <span className="text-gray-300"> hit </span>
            <span className="text-white">{entry.target}</span>
            <span className="text-gray-300"> for </span>
            <span className="text-orange-400">{entry.damage}</span>
            <span className="text-gray-300"> damage</span>
          </>
        );
      case 'miss':
        return (
          <>
            <span className={actorColor}>{actor}</span>
            <span className="text-gray-400"> missed </span>
            <span className="text-white">{entry.target}</span>
          </>
        );
      case 'killed':
        return (
          <>
            <span className={actorColor}>{actor}</span>
            <span className="text-green-400"> killed </span>
            <span className="text-white">{entry.target}</span>
            <span className="text-green-400">!</span>
          </>
        );
      case 'defended':
        return (
          <>
            <span className={actorColor}>{actor}</span>
            <span className="text-blue-300"> raised their guard (+2 AC)</span>
          </>
        );
      case 'fled':
        return (
          <>
            <span className={actorColor}>{actor}</span>
            <span className="text-yellow-300"> fled from combat!</span>
          </>
        );
      case 'failed':
        return (
          <>
            <span className={actorColor}>{actor}</span>
            <span className="text-red-300"> failed to escape!</span>
          </>
        );
      default:
        return (
          <>
            <span className={actorColor}>{actor}</span>
            <span className="text-gray-300"> {entry.action}</span>
          </>
        );
    }
  };

  return (
    <div className="mb-1">
      <span className="text-gray-600 text-xs mr-2">R{entry.round}</span>
      {getMessage()}
    </div>
  );
}
