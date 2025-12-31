/**
 * Root application component for Chaos Dungeon.
 *
 * This is the main entry point for the React application.
 * Future features will include:
 * - Character creation
 * - Game session management
 * - Chat interface with AI DM
 */

function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 py-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-amber-500 font-fantasy">
            Chaos Dungeon
          </h1>
          <p className="text-slate-400 mt-1">
            A text-based RPG with an AI Dungeon Master
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-xl font-semibold text-amber-400 mb-4">
            Welcome, Adventurer
          </h2>
          <p className="text-slate-300 mb-4">
            You stand at the entrance of the Chaos Dungeon, a place where fate
            is determined by dice rolls and the whims of a mysterious Dungeon
            Master.
          </p>
          <p className="text-slate-400 text-sm">
            Game features coming soon:
          </p>
          <ul className="list-disc list-inside text-slate-400 text-sm mt-2 space-y-1">
            <li>Create your character using BECMI D&D rules</li>
            <li>Explore procedurally generated dungeons</li>
            <li>Engage in turn-based combat</li>
            <li>Make choices that shape your adventure</li>
          </ul>

          {/* Placeholder for future game UI */}
          <div className="mt-6 p-4 bg-slate-900 rounded border border-slate-600 text-center">
            <p className="text-slate-500 italic">
              The adventure awaits...
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700 px-4 py-3">
        <div className="max-w-4xl mx-auto text-center text-sm text-slate-500">
          Powered by Claude AI &bull; BECMI D&D Rules (1983)
        </div>
      </footer>
    </div>
  );
}

export default App;
