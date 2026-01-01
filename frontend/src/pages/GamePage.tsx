/**
 * Game page placeholder.
 * Full implementation in init-07-game-ui.
 */
import { useParams, Link } from 'react-router-dom';
import { Button, Card } from '../components';

/**
 * Placeholder game page showing session ID.
 */
export function GamePage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  return (
    <div className="max-w-2xl mx-auto text-center py-12">
      <Card>
        <h1 className="text-3xl font-fantasy text-amber-500 mb-4">
          Game Session
        </h1>

        <div className="space-y-6">
          <div className="bg-slate-900 rounded-lg p-4">
            <p className="text-sm text-slate-400 mb-1">Session ID</p>
            <code className="text-amber-500 font-mono text-sm break-all">
              {sessionId}
            </code>
          </div>

          <div className="border border-dashed border-slate-600 rounded-lg p-8">
            <p className="text-slate-400 mb-2">
              Game UI coming in init-07-game-ui
            </p>
            <p className="text-sm text-slate-500">
              The chat interface, message history, and game controls
              will be implemented in the next phase.
            </p>
          </div>

          <Link to="/characters">
            <Button variant="secondary">Back to Characters</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
