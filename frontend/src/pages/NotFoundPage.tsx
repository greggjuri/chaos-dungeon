/**
 * 404 Not Found page.
 */
import { Link } from 'react-router-dom';
import { Button, Card } from '../components';

/**
 * Page displayed when route is not found.
 */
export function NotFoundPage() {
  return (
    <div className="max-w-md mx-auto text-center py-16">
      <Card>
        <h1 className="text-6xl font-fantasy text-amber-500 mb-4">404</h1>
        <h2 className="text-2xl font-bold text-slate-100 mb-4">
          Lost in the Dungeon
        </h2>
        <p className="text-slate-400 mb-8">
          The page you seek has vanished into the shadows.
          Perhaps it never existed at all...
        </p>
        <Link to="/">
          <Button>Return to Safety</Button>
        </Link>
      </Card>
    </div>
  );
}
