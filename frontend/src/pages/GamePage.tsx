/**
 * Game page with full chat interface and game UI.
 */
import { useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useGameSession } from '../hooks';
import {
  ActionInput,
  CharacterStatus,
  ChatHistory,
  CombatStatus,
  CombatUI,
  DeathScreen,
  InventoryPanel,
  TokenCounter,
} from '../components/game';
import { Button, Card, Loading } from '../components';
import { Item } from '../types';

/**
 * Main game page with chat interface, character status,
 * combat display, and action input.
 */
export function GamePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [showInventory, setShowInventory] = useState(false);
  const [inventoryHeight, setInventoryHeight] = useState(200);

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
    // Character has full Item objects
    return character.inventory;
  }, [character]);

  // Handle inventory panel resize via drag
  const handleInventoryDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = inventoryHeight;

    const handleMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientY - startY;
      const newHeight = Math.max(100, Math.min(startHeight + delta, window.innerHeight * 0.5));
      setInventoryHeight(newHeight);
    };

    const handleUp = () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  }, [inventoryHeight]);

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
          <div className="text-red-400 text-4xl mb-4">⚠️</div>
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
    <div className="flex flex-col h-screen bg-gray-900 overflow-hidden">
      {/* Fixed header section - never scrolls */}
      <header className="flex-shrink-0 bg-gray-900 z-10">
        {/* Character status bar */}
        <CharacterStatus character={character} snapshot={characterSnapshot} />

        {/* Inventory toggle bar */}
        <div className="bg-gray-800/50 border-b border-gray-700 px-4 py-1">
          <button
            onClick={() => setShowInventory(!showInventory)}
            className="text-amber-400 hover:text-amber-300 text-sm font-medium flex items-center gap-1"
          >
            <span>{showInventory ? '▼' : '▶'}</span>
            <span>Inventory ({inventoryItems.length})</span>
          </button>
        </div>

        {/* Collapsible inventory panel with resizable height */}
        {showInventory && (
          <div
            className="bg-gray-800/80 border-b border-gray-700 overflow-y-auto relative"
            style={{ height: `${inventoryHeight}px` }}
          >
            <InventoryPanel
              items={inventoryItems}
              inCombat={combatActive || (combat?.active ?? false)}
              onUseItem={handleUseItem}
            />
            {/* Drag handle for resizing */}
            <div
              className="absolute bottom-0 left-0 right-0 h-2 bg-gray-700 cursor-ns-resize hover:bg-amber-600 transition-colors"
              onMouseDown={handleInventoryDragStart}
            />
          </div>
        )}

        {/* Error toast */}
        {error && (
          <div className="mx-4 mt-2 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}
      </header>

      {/* Scroll containment wrapper - flex-1 min-h-0 is critical for proper containment */}
      <div className="flex-1 min-h-0 overflow-hidden">
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

      {/* Token counter overlay - toggle with 'T' key */}
      <TokenCounter usage={usage} />
    </div>
  );
}
