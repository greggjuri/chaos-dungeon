/**
 * Character list page.
 */
import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button, Card, Loading } from '../components';
import { characterService } from '../services';
import { CharacterSummary, ApiRequestError } from '../types';

const classDisplayNames: Record<string, string> = {
  fighter: 'Fighter',
  thief: 'Thief',
  magic_user: 'Magic-User',
  cleric: 'Cleric',
};

/**
 * Lists user's characters with options to create new or start session.
 */
export function CharactersPage() {
  const navigate = useNavigate();
  const [characters, setCharacters] = useState<CharacterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadCharacters = useCallback(async () => {
    try {
      setError(null);
      const response = await characterService.list();
      setCharacters(response.characters);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.error);
      } else {
        setError('Failed to load characters');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCharacters();
  }, [loadCharacters]);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete ${name}? This cannot be undone.`)) {
      return;
    }

    setDeleting(id);
    try {
      await characterService.delete(id);
      setCharacters((prev) => prev.filter((c) => c.character_id !== id));
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.error);
      } else {
        setError('Failed to delete character');
      }
    } finally {
      setDeleting(null);
    }
  };

  const handleStartSession = (characterId: string) => {
    navigate(`/sessions/new?character=${characterId}`);
  };

  if (loading) {
    return <Loading message="Loading characters..." />;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-fantasy text-amber-500">Your Characters</h1>
        <Link to="/characters/new">
          <Button>Create New Character</Button>
        </Link>
      </div>

      {error && (
        <Card className="bg-red-900/50 border-red-700">
          <p className="text-red-200">{error}</p>
        </Card>
      )}

      {characters.length === 0 ? (
        <Card className="text-center py-12">
          <p className="text-slate-400 mb-4">
            You haven&apos;t created any characters yet.
          </p>
          <Link to="/characters/new">
            <Button>Create Your First Character</Button>
          </Link>
        </Card>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {characters.map((character) => (
            <Card key={character.character_id} hoverable>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold text-slate-100">
                    {character.name}
                  </h3>
                  <p className="text-amber-500">
                    Level {character.level}{' '}
                    {classDisplayNames[character.character_class]}
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={() => handleStartSession(character.character_id)}
                  className="flex-1"
                >
                  Play
                </Button>
                <Button
                  variant="danger"
                  onClick={() =>
                    handleDelete(character.character_id, character.name)
                  }
                  loading={deleting === character.character_id}
                  disabled={deleting !== null}
                >
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
