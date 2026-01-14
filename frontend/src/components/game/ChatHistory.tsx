/**
 * Scrollable chat history component.
 */
import { useEffect, useRef } from 'react';
import { GameMessage } from '../../types';
import { ChatMessage } from './ChatMessage';

interface Props {
  messages: GameMessage[];
  isLoading?: boolean;
}

/**
 * Scrollable container for chat messages.
 * Auto-scrolls to bottom when new messages arrive.
 */
export function ChatHistory({ messages, isLoading = false }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  return (
    <div
      ref={containerRef}
      className="h-full px-4 py-4 space-y-4"
    >
      {messages.length === 0 && !isLoading && (
        <div className="text-center text-gray-500 py-8">
          <p>Your adventure awaits...</p>
          <p className="text-sm mt-2">Type your action below to begin.</p>
        </div>
      )}

      {messages.map((message, idx) => (
        <ChatMessage key={idx} message={message} />
      ))}

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400 pl-4">
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-amber-500 rounded-full animate-bounce" />
            <span
              className="w-2 h-2 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: '0.1s' }}
            />
            <span
              className="w-2 h-2 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: '0.2s' }}
            />
          </div>
          <span className="text-sm">The Dungeon Master is thinking...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
