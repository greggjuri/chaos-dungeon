/**
 * Version display component.
 * Shows app version in bottom-right corner on all pages.
 */
export function Version() {
  return (
    <div className="fixed bottom-2 right-2 text-gray-600 text-xs z-40 pointer-events-none select-none">
      v{__APP_VERSION__}
    </div>
  );
}
