/**
 * New session creation page.
 */
import { useState, useEffect, useCallback, FormEvent } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Button, Card, Select, Loading } from '../components';
import { characterService, sessionService } from '../services';
import { CharacterSummary, CampaignSetting, ApiRequestError } from '../types';

interface CampaignOption {
  value: CampaignSetting;
  name: string;
  description: string;
}

const campaignOptions: CampaignOption[] = [
  {
    value: 'default',
    name: 'Classic Adventure',
    description: 'Begin at the Rusty Tankard tavern. Open-ended exploration awaits.',
  },
  {
    value: 'dark_forest',
    name: 'The Dark Forest',
    description: 'Ancient evil stirs in the twisted woods. Will you uncover its secrets?',
  },
  {
    value: 'cursed_castle',
    name: 'The Cursed Castle',
    description: 'A haunted fortress filled with undead horrors and forgotten treasures.',
  },
  {
    value: 'forgotten_mines',
    name: 'The Forgotten Mines',
    description: 'Deep beneath the mountains, something waits in the darkness.',
  },
];

const classDisplayNames: Record<string, string> = {
  fighter: 'Fighter',
  thief: 'Thief',
  magic_user: 'Magic-User',
  cleric: 'Cleric',
};

/**
 * Session creation form with character and campaign selection.
 */
export function NewSessionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedCharacter = searchParams.get('character');

  const [characters, setCharacters] = useState<CharacterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCharacter, setSelectedCharacter] = useState<string>(
    preselectedCharacter || ''
  );
  const [selectedCampaign, setSelectedCampaign] =
    useState<CampaignSetting>('default');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCharacters = useCallback(async () => {
    try {
      const response = await characterService.list();
      setCharacters(response.characters);

      // Auto-select if only one character
      if (response.characters.length === 1 && !preselectedCharacter) {
        setSelectedCharacter(response.characters[0].character_id);
      }
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.error);
      } else {
        setError('Failed to load characters');
      }
    } finally {
      setLoading(false);
    }
  }, [preselectedCharacter]);

  useEffect(() => {
    loadCharacters();
  }, [loadCharacters]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!selectedCharacter) {
      setError('Please select a character');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const session = await sessionService.create({
        character_id: selectedCharacter,
        campaign_setting: selectedCampaign,
      });
      navigate(`/play/${session.session_id}`);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        if (err.status === 409) {
          setError('You have reached the maximum number of sessions (10). Delete an old session to create a new one.');
        } else {
          setError(err.error);
        }
      } else {
        setError('Failed to create session');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <Loading message="Loading characters..." />;
  }

  if (characters.length === 0) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <Card>
          <h1 className="text-2xl font-fantasy text-amber-500 mb-4">
            No Characters Found
          </h1>
          <p className="text-slate-400 mb-6">
            You need to create a character before starting a game.
          </p>
          <Link to="/characters/new">
            <Button>Create Character</Button>
          </Link>
        </Card>
      </div>
    );
  }

  const characterOptions = characters.map((c) => ({
    value: c.character_id,
    label: `${c.name} - Level ${c.level} ${classDisplayNames[c.character_class]}`,
  }));

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-fantasy text-amber-500">New Adventure</h1>
        <Link to="/characters">
          <Button variant="secondary">Cancel</Button>
        </Link>
      </div>

      {error && (
        <Card className="bg-red-900/50 border-red-700">
          <p className="text-red-200">{error}</p>
        </Card>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Character Selection */}
        <Card>
          <h2 className="text-lg font-bold text-slate-100 mb-4">
            Choose Your Hero
          </h2>
          <Select
            label="Character"
            options={characterOptions}
            value={selectedCharacter}
            onChange={(e) => setSelectedCharacter(e.target.value)}
            placeholder="Select a character"
          />
        </Card>

        {/* Campaign Selection */}
        <Card>
          <h2 className="text-lg font-bold text-slate-100 mb-4">
            Choose Your Destiny
          </h2>
          <div className="grid gap-3">
            {campaignOptions.map((campaign) => (
              <label
                key={campaign.value}
                className={`
                  flex items-start gap-3 p-4 rounded-lg cursor-pointer
                  border transition-colors
                  ${
                    selectedCampaign === campaign.value
                      ? 'bg-amber-900/30 border-amber-600'
                      : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                  }
                `}
              >
                <input
                  type="radio"
                  name="campaign"
                  value={campaign.value}
                  checked={selectedCampaign === campaign.value}
                  onChange={() => setSelectedCampaign(campaign.value)}
                  className="mt-1 text-amber-500 focus:ring-amber-500"
                />
                <div>
                  <span className="font-medium text-slate-100">
                    {campaign.name}
                  </span>
                  <p className="text-sm text-slate-400">{campaign.description}</p>
                </div>
              </label>
            ))}
          </div>
        </Card>

        {/* Submit Button */}
        <Button
          type="submit"
          loading={submitting}
          disabled={!selectedCharacter}
          className="w-full py-3 text-lg"
        >
          Begin Adventure
        </Button>
      </form>
    </div>
  );
}
