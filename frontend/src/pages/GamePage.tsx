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
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-900">
      {/* Fixed header section - never scrolls */}
      <div className="flex-shrink-0">
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

        {/* Collapsible inventory panel */}
        {showInventory && (
          <div className="bg-gray-800/80 border-b border-gray-700 max-h-48 overflow-y-auto">
            <InventoryPanel
              items={inventoryItems}
              inCombat={combatActive || (combat?.active ?? false)}
              onUseItem={handleUseItem}
            />
          </div>
        )}

        {/* Error toast */}
        {error && (
          <div className="mx-4 mt-2 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Chat history - scrollable middle */}
      <ChatHistory messages={messages} isLoading={isSendingAction} />

      {/* Combat UI - shown when turn-based combat is active */}
      {combat && combat.active && (
        <CombatUI
          combat={combat}
          onAction={sendCombatAction}
          isLoading={isSendingAction}
        />
      )}

      {/* Legacy combat status - shown when combat active but no turn-based UI */}
      {combatActive && (!combat || !combat.active) && (
        <CombatStatus enemies={enemies} combatActive={combatActive} />
      )}

      {/* Death screen - shown inline at bottom when character dies */}
      {characterDead && (
        <DeathScreen character={character} snapshot={characterSnapshot} />
      )}

      {/* Action input - always shown when not dead (can type during combat too) */}
      {!characterDead && (
        <ActionInput
          onSend={sendAction}
          disabled={sessionEnded}
          isLoading={isSendingAction}
          placeholder={combat?.active ? 'Type action or use buttons above...' : 'What do you do?'}
        />
      )}

      {/* Token counter overlay - toggle with 'T' key */}
      <TokenCounter usage={usage} />
    </div>
  );
}
