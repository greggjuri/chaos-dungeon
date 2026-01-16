/**
 * Reusable panel overlay component for modal dialogs.
 * Provides a centered panel with backdrop, title bar, and close functionality.
 */
import { X } from 'lucide-react';
import { ReactNode } from 'react';

interface PanelOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  icon: ReactNode;
  children: ReactNode;
}

/**
 * Modal overlay with centered panel.
 * Click outside panel to close.
 */
export function PanelOverlay({ isOpen, onClose, title, icon, children }: PanelOverlayProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-gray-900/95 border border-gray-700 rounded-lg w-full max-w-md mx-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2 text-amber-400 font-bold">
            {icon}
            <span>{title}</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors"
            aria-label="Close panel"
          >
            <X size={20} />
          </button>
        </div>
        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
