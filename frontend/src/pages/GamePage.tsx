/**
 * Game page with full chat interface and game UI.
 */
import { useParams, Link } from 'react-router-dom';
import { useGameSession } from '../hooks';
import {
  ActionInput,
  CharacterStatus,
  ChatHistory,
  CombatStatus,
  CombatUI,
  DeathScreen,
  TokenCounter,
} from '../components/game';
import { Button, Card, Loading } from '../components';

/**
 * Main game page with chat interface, character status,
 * combat display, and action input.
 */
export function GamePage() {
  const { sessionId } = useParams<{ sessionId: string }>();

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

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-900">
      {/* Character status bar - sticky top */}
      <CharacterStatus character={character} snapshot={characterSnapshot} />

      {/* Error toast */}
      {error && (
        <div className="mx-4 mt-2 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
          {error}
        </div>
      )}

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
