/**
 * Game options panel for player preferences.
 * Controls gore level, mature content, and combat confirmation.
 */
import { Settings } from 'lucide-react';
import { PanelOverlay } from './PanelOverlay';
import {
  GameOptions,
  GoreLevel,
  MatureContentLevel,
} from '../../types';

interface OptionsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  options: GameOptions;
  onOptionsChange: (options: GameOptions) => void;
  isSaving?: boolean;
}

const GORE_LEVELS: { value: GoreLevel; label: string; description: string }[] = [
  { value: 'mild', label: 'Mild', description: 'Violence outcomes without graphic detail' },
  { value: 'standard', label: 'Standard', description: 'Moderate gore, visceral but not excessive' },
  { value: 'extreme', label: 'Extreme', description: 'Full graphic detail and viscera' },
];

const MATURE_LEVELS: { value: MatureContentLevel; label: string; description: string }[] = [
  { value: 'fade_to_black', label: 'Fade to Black', description: 'Romantic scenes cut away' },
  { value: 'suggestive', label: 'Suggestive', description: 'Sensual but not explicit' },
  { value: 'explicit', label: 'Explicit', description: 'Full adult content' },
];

/**
 * Game options panel component.
 */
export function OptionsPanel({
  isOpen,
  onClose,
  options,
  onOptionsChange,
  isSaving = false,
}: OptionsPanelProps) {
  const handleToggle = (key: keyof GameOptions) => {
    if (typeof options[key] === 'boolean') {
      onOptionsChange({
        ...options,
        [key]: !options[key],
      });
    }
  };

  const handleGoreChange = (value: GoreLevel) => {
    onOptionsChange({
      ...options,
      gore_level: value,
    });
  };

  const handleMatureChange = (value: MatureContentLevel) => {
    onOptionsChange({
      ...options,
      mature_content: value,
    });
  };

  return (
    <PanelOverlay
      isOpen={isOpen}
      onClose={onClose}
      title="Game Options"
      icon={<Settings size={18} />}
    >
      <div className="p-4 space-y-6">
        {/* Combat Confirmation Toggle */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-gray-200 font-medium">
              Confirm Combat (Non-Hostiles)
            </label>
            <button
              onClick={() => handleToggle('confirm_combat_noncombat')}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                options.confirm_combat_noncombat
                  ? 'bg-amber-600'
                  : 'bg-gray-600'
              }`}
              disabled={isSaving}
              aria-pressed={options.confirm_combat_noncombat}
            >
              <span
                className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform ${
                  options.confirm_combat_noncombat ? 'translate-x-6' : ''
                }`}
              />
            </button>
          </div>
          <p className="text-sm text-gray-400">
            Ask for confirmation before attacking non-hostile NPCs
          </p>
        </div>

        {/* Gore Level */}
        <div className="space-y-2">
          <label className="text-gray-200 font-medium block">
            Gore Level
          </label>
          <div className="space-y-1">
            {GORE_LEVELS.map((level) => (
              <button
                key={level.value}
                onClick={() => handleGoreChange(level.value)}
                disabled={isSaving}
                className={`w-full text-left px-3 py-2 rounded transition-colors ${
                  options.gore_level === level.value
                    ? 'bg-amber-900/50 border border-amber-600 text-amber-200'
                    : 'bg-gray-800 border border-gray-700 text-gray-300 hover:border-gray-600'
                }`}
              >
                <div className="font-medium">{level.label}</div>
                <div className="text-xs text-gray-400">{level.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Mature Content Level */}
        <div className="space-y-2">
          <label className="text-gray-200 font-medium block">
            Mature Content
          </label>
          <div className="space-y-1">
            {MATURE_LEVELS.map((level) => (
              <button
                key={level.value}
                onClick={() => handleMatureChange(level.value)}
                disabled={isSaving}
                className={`w-full text-left px-3 py-2 rounded transition-colors ${
                  options.mature_content === level.value
                    ? 'bg-amber-900/50 border border-amber-600 text-amber-200'
                    : 'bg-gray-800 border border-gray-700 text-gray-300 hover:border-gray-600'
                }`}
              >
                <div className="font-medium">{level.label}</div>
                <div className="text-xs text-gray-400">{level.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Saving indicator */}
        {isSaving && (
          <div className="text-center text-amber-400 text-sm">
            Saving...
          </div>
        )}
      </div>
    </PanelOverlay>
  );
}
