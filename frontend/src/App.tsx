/**
 * Root application component for Chaos Dungeon.
 *
 * Sets up React Router and provides global context.
 */
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import { UserProvider } from './context';
import { AppLayout, AgeGate } from './components';
import {
  HomePage,
  CharactersPage,
  NewCharacterPage,
  NewSessionPage,
  GamePage,
  NotFoundPage,
} from './pages';

/**
 * Root layout with providers and age gate.
 */
function RootLayout() {
  return (
    <UserProvider>
      <AgeGate />
      <AppLayout>
        <Outlet />
      </AppLayout>
    </UserProvider>
  );
}

/**
 * Application router configuration.
 */
const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/characters', element: <CharactersPage /> },
      { path: '/characters/new', element: <NewCharacterPage /> },
      { path: '/sessions/new', element: <NewSessionPage /> },
      { path: '/play/:sessionId', element: <GamePage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

/**
 * Main App component with router provider.
 */
export default function App() {
  return <RouterProvider router={router} />;
}
