/**
 * Game page with full chat interface and game UI.
 */
import { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Package, User } from 'lucide-react';
import { useGameSession } from '../hooks';
import {
  ActionInput,
  CharacterSheet,
  CharacterStatus,
  ChatHistory,
  CombatStatus,
  CombatUI,
  DeathScreen,
  InventoryPanel,
  KeyboardHint,
  OptionsPanel,
  PanelOverlay,
  TokenCounter,
} from '../components/game';
import { Button, Card, Loading } from '../components';
import { Item, GameOptions, DEFAULT_GAME_OPTIONS } from '../types';
import { sessionService } from '../services/sessions';

/** Panel type for overlay system */
type PanelType = 'inventory' | 'character' | 'options' | null;

/**
 * Main game page with chat interface, character status,
 * combat display, and action input.
 */
export function GamePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [activePanel, setActivePanel] = useState<PanelType>(null);
  const [options, setOptions] = useState<GameOptions>(DEFAULT_GAME_OPTIONS);
  const [isSavingOptions, setIsSavingOptions] = useState(false);

  // Prevent document-level scrolling on game page
  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;

    // Save original values
    const originalHtmlOverflow = html.style.overflow;
    const originalBodyOverflow = body.style.overflow;

    // Disable scrolling
    html.style.overflow = 'hidden';
    body.style.overflow = 'hidden';

    return () => {
      // Restore on unmount
      html.style.overflow = originalHtmlOverflow;
      body.style.overflow = originalBodyOverflow;
    };
  }, []);

  // Keyboard shortcuts for panel navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip if typing in input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      // Skip if modifier keys held
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      switch (e.key.toLowerCase()) {
        case 'i':
          e.preventDefault();
          setActivePanel((prev) => (prev === 'inventory' ? null : 'inventory'));
          break;
        case 'c':
          e.preventDefault();
          setActivePanel((prev) => (prev === 'character' ? null : 'character'));
          break;
        case 'o':
          e.preventDefault();
          setActivePanel((prev) => (prev === 'options' ? null : 'options'));
          break;
        case 'escape':
          e.preventDefault();
          setActivePanel(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const {
    session,
    character,
    characterSnapshot,
    messages,
    combatActive,
    enemies,
    combat,
    characterDead,
    sessionEnded,
    isLoading,
    isSendingAction,
    error,
    usage,
    sendAction,
    sendCombatAction,
    retryLoad,
  } = useGameSession(sessionId || '');

  // Sync options from session when it loads
  useEffect(() => {
    if (session?.options) {
      setOptions(session.options);
    }
  }, [session?.options]);

  // Handle options change - save to server
  const handleOptionsChange = useCallback(
    async (newOptions: GameOptions) => {
      if (!sessionId) return;
      setOptions(newOptions);
      setIsSavingOptions(true);
      try {
        await sessionService.updateOptions(sessionId, newOptions);
      } catch (err) {
        console.error('Failed to save options:', err);
        // Revert on error - but keep UI responsive, so we don't revert
      } finally {
        setIsSavingOptions(false);
      }
    },
    [sessionId]
  );

  // Handle using an item from inventory (during combat)
  const handleUseItem = useCallback(
    (itemId: string) => {
      sendCombatAction({ action_type: 'use_item', item_id: itemId });
    },
    [sendCombatAction]
  );

  // Get current inventory from character or snapshot
  const getInventoryItems = useCallback((): Item[] => {
    if (!character) return [];
    // Use snapshot inventory if available (most recent), otherwise character
    return characterSnapshot?.inventory ?? character.inventory;
  }, [character, characterSnapshot]);

  // Panel handlers
  const closePanel = useCallback(() => setActivePanel(null), []);
  const openInventory = useCallback(() => setActivePanel('inventory'), []);
  const openCharacter = useCallback(() => setActivePanel('character'), []);
  const openOptions = useCallback(() => setActivePanel('options'), []);

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <Loading size="lg" message="Loading adventure..." />
      </div>
    );
  }

  // Show error state
  if (error && !session) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <Card>
          <div className="text-red-400 text-4xl mb-4">Warning</div>
          <h1 className="text-xl font-bold text-white mb-2">
            Failed to Load Session
          </h1>
          <p className="text-gray-400 mb-6">{error}</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button onClick={retryLoad} variant="primary">
              Try Again
            </Button>
            <Link to="/characters">
              <Button variant="secondary">Back to Characters</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  // No session or character found
  if (!session || !character) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <Card>
          <h1 className="text-xl font-bold text-white mb-2">Session Not Found</h1>
          <p className="text-gray-400 mb-6">
            This session may have been deleted or never existed.
          </p>
          <Link to="/characters">
            <Button variant="primary">Back to Characters</Button>
          </Link>
        </Card>
      </div>
    );
  }

  const inventoryItems = getInventoryItems();

  return (
    <div className="flex flex-col h-[calc(100vh-178px)] bg-gray-900 overflow-hidden">
      {/* Fixed header section - never scrolls */}
      <header className="flex-shrink-0 bg-gray-900 z-10">
        {/* Character status bar with panel icons */}
        <CharacterStatus
          character={character}
          snapshot={characterSnapshot}
          onInventoryClick={openInventory}
          onCharacterClick={openCharacter}
          onOptionsClick={openOptions}
        />

        {/* Error toast */}
        {error && (
          <div className="mx-4 mt-2 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}
      </header>

      {/* Scroll containment wrapper - flex-1 min-h-0 is critical for proper containment */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        <ChatHistory messages={messages} isLoading={isSendingAction} />
      </div>

      {/* Combat UI - shown when turn-based combat is active */}
      {combat && combat.active && (
        <div className="flex-shrink-0">
          <CombatUI
            combat={combat}
            onAction={sendCombatAction}
            isLoading={isSendingAction}
          />
        </div>
      )}

      {/* Legacy combat status - shown when combat active but no turn-based UI */}
      {combatActive && (!combat || !combat.active) && (
        <div className="flex-shrink-0">
          <CombatStatus enemies={enemies} combatActive={combatActive} />
        </div>
      )}

      {/* Death screen - shown inline at bottom when character dies */}
      {characterDead && (
        <div className="flex-shrink-0">
          <DeathScreen character={character} snapshot={characterSnapshot} />
        </div>
      )}

      {/* Action input - fixed at bottom, shown when not dead */}
      {!characterDead && (
        <div className="flex-shrink-0">
          <ActionInput
            onSend={sendAction}
            disabled={sessionEnded}
            isLoading={isSendingAction}
            placeholder={combat?.active ? 'Type action or use buttons above...' : 'What do you do?'}
          />
        </div>
      )}

      {/* Keyboard hint - shown when no panel is open */}
      <KeyboardHint visible={activePanel === null} />

      {/* Token counter overlay - toggle with 'T' key */}
      <TokenCounter usage={usage} />

      {/* Inventory Panel Overlay */}
      <PanelOverlay
        isOpen={activePanel === 'inventory'}
        onClose={closePanel}
        title="Inventory"
        icon={<Package size={20} />}
      >
        <InventoryPanel
          items={inventoryItems}
          inCombat={combatActive || (combat?.active ?? false)}
          onUseItem={handleUseItem}
        />
      </PanelOverlay>

      {/* Character Sheet Panel Overlay */}
      <PanelOverlay
        isOpen={activePanel === 'character'}
        onClose={closePanel}
        title="Character"
        icon={<User size={20} />}
      >
        <CharacterSheet character={character} snapshot={characterSnapshot} />
      </PanelOverlay>

      {/* Options Panel */}
      <OptionsPanel
        isOpen={activePanel === 'options'}
        onClose={closePanel}
        options={options}
        onOptionsChange={handleOptionsChange}
        isSaving={isSavingOptions}
      />
    </div>
  );
}
