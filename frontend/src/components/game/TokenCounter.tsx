/**
 * Token usage counter for debugging/testing.
 * Displays current session and global token usage.
 * Toggle visibility with 'T' key.
 */
import { useState, useEffect, useCallback } from 'react';
import { UsageStats } from '../../types';

interface TokenCounterProps {
  usage: UsageStats | null;
}

const STORAGE_KEY = 'chaos-dungeon-token-counter-visible';

/**
 * Format number with commas for readability.
 */
function formatNumber(n: number): string {
  return n.toLocaleString();
}

/**
 * Token counter overlay component.
 * Shows session and global token usage in bottom-right corner.
 * Press 'T' to toggle visibility (persisted in localStorage).
 */
export function TokenCounter({ usage }: TokenCounterProps) {
  const [isVisible, setIsVisible] = useState(() => {
    // Load initial visibility from localStorage
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === 'true';
  });

  // Toggle visibility and persist to localStorage
  const toggleVisibility = useCallback(() => {
    setIsVisible((prev) => {
      const newValue = !prev;
      localStorage.setItem(STORAGE_KEY, String(newValue));
      return newValue;
    });
  }, []);

  // Handle keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger on 'T' key when not typing in an input
      if (
        e.key === 't' &&
        !e.ctrlKey &&
        !e.metaKey &&
        !e.altKey &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement)
      ) {
        toggleVisibility();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleVisibility]);

  // Don't render if hidden or no usage data
  if (!isVisible) {
    return null;
  }

  // Show placeholder if no data yet
  if (!usage) {
    return (
      <div className="fixed bottom-16 right-4 z-50 bg-black/70 text-gray-400 text-xs font-mono px-3 py-2 rounded-lg backdrop-blur-sm">
        <div>Session: --/--</div>
        <div>Global: --/--</div>
        <div className="text-gray-600 mt-1">Press T to hide</div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-16 right-4 z-50 bg-black/70 text-gray-300 text-xs font-mono px-3 py-2 rounded-lg backdrop-blur-sm">
      <div>
        Session: {formatNumber(usage.session_tokens)} /{' '}
        {formatNumber(usage.session_limit)}
      </div>
      <div>
        Global: {formatNumber(usage.global_tokens)} /{' '}
        {formatNumber(usage.global_limit)}
      </div>
      <div className="text-gray-600 mt-1">Press T to hide</div>
    </div>
  );
}
