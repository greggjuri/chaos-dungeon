/**
 * Application header with navigation.
 */
import { Link } from 'react-router-dom';
import { useUser } from '../../context';

/**
 * Navigation header with logo and links.
 */
export function Header() {
  const { ageVerified } = useUser();

  return (
    <header className="bg-slate-900 border-b border-slate-800">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl font-fantasy text-amber-500">
              Chaos Dungeon
            </span>
          </Link>

          {/* Navigation - only show when age verified */}
          {ageVerified && (
            <nav className="flex items-center gap-6">
              <Link
                to="/characters"
                className="text-slate-300 hover:text-amber-500 transition-colors"
              >
                Characters
              </Link>
              <Link
                to="/sessions/new"
                className="text-slate-300 hover:text-amber-500 transition-colors"
              >
                New Game
              </Link>
            </nav>
          )}
        </div>
      </div>
    </header>
  );
}
