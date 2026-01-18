/**
 * Keyboard shortcut hint text displayed at the bottom of the game UI.
 */

interface KeyboardHintProps {
  visible: boolean;
}

/**
 * Small hint text showing available keyboard shortcuts.
 * Hidden when a panel is open or when not relevant.
 */
export function KeyboardHint({ visible }: KeyboardHintProps) {
  if (!visible) return null;

  return (
    <div className="fixed bottom-2 left-1/2 -translate-x-1/2 z-30 text-gray-600 text-xs pointer-events-none">
      I Inventory · C Character · O Options · Esc Close
    </div>
  );
}
