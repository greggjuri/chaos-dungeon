/**
 * Player action input component.
 */
import { useState, useCallback, KeyboardEvent } from 'react';

interface Props {
  onSend: (action: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

const MAX_LENGTH = 500;

/**
 * Text input for player actions.
 * Enter submits, Shift+Enter adds newline.
 */
export function ActionInput({ onSend, disabled = false, isLoading = false }: Props) {
  const [value, setValue] = useState('');

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && !disabled && !isLoading) {
      onSend(trimmed);
      setValue('');
    }
  }, [value, disabled, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const isDisabled = disabled || isLoading;
  const isEmpty = value.trim().length === 0;

  return (
    <div className="border-t border-gray-700 bg-gray-800 p-4">
      <div className="flex gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value.slice(0, MAX_LENGTH))}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled
              ? 'Session has ended'
              : "What do you do? (Enter to send, Shift+Enter for newline)"
          }
          disabled={isDisabled}
          rows={2}
          className={`
            flex-1 px-3 py-2 rounded-lg resize-none
            bg-gray-700 border border-gray-600
            text-gray-100 placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        />
        <button
          onClick={handleSubmit}
          disabled={isDisabled || isEmpty}
          className={`
            px-4 py-2 rounded-lg font-medium
            bg-amber-600 text-white
            hover:bg-amber-500
            focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 focus:ring-offset-gray-800
            disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-amber-600
            transition-colors
          `}
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg
                className="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </span>
          ) : (
            'Send'
          )}
        </button>
      </div>
      <div className="flex justify-end mt-1">
        <span className="text-xs text-gray-500">
          {value.length}/{MAX_LENGTH}
        </span>
      </div>
    </div>
  );
}
