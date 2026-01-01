/**
 * Character creation page.
 */
import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button, Card, Input } from '../components';
import { characterService } from '../services';
import { CharacterClass, AbilityScores, ApiRequestError } from '../types';

interface ClassOption {
  value: CharacterClass;
  name: string;
  description: string;
}

const classOptions: ClassOption[] = [
  {
    value: 'fighter',
    name: 'Fighter',
    description: 'Masters of combat. High HP, all weapons and armor.',
  },
  {
    value: 'thief',
    name: 'Thief',
    description: 'Skilled rogues. Stealth, backstab, light armor.',
  },
  {
    value: 'magic_user',
    name: 'Magic-User',
    description: 'Wielders of arcane power. Spells but low HP, no armor.',
  },
  {
    value: 'cleric',
    name: 'Cleric',
    description: 'Divine warriors. Healing, turn undead, medium armor.',
  },
];

/**
 * Roll 3d6 for an ability score.
 */
function roll3d6(): number {
  return (
    Math.floor(Math.random() * 6) +
    Math.floor(Math.random() * 6) +
    Math.floor(Math.random() * 6) +
    3
  );
}

/**
 * Generate random ability scores.
 */
function rollAbilities(): AbilityScores {
  return {
    strength: roll3d6(),
    intelligence: roll3d6(),
    wisdom: roll3d6(),
    dexterity: roll3d6(),
    constitution: roll3d6(),
    charisma: roll3d6(),
  };
}

/**
 * Character creation form with class selection and ability rolls.
 */
export function NewCharacterPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [nameError, setNameError] = useState('');
  const [selectedClass, setSelectedClass] = useState<CharacterClass>('fighter');
  const [abilities, setAbilities] = useState<AbilityScores | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRoll = () => {
    setAbilities(rollAbilities());
  };

  const validateName = (value: string): boolean => {
    if (value.length < 3) {
      setNameError('Name must be at least 3 characters');
      return false;
    }
    if (value.length > 30) {
      setNameError('Name must be 30 characters or less');
      return false;
    }
    setNameError('');
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!validateName(name)) {
      return;
    }

    if (!abilities) {
      setError('Please roll your abilities first');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await characterService.create({
        name,
        character_class: selectedClass,
        abilities,
      });
      navigate('/characters');
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.error);
      } else {
        setError('Failed to create character');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-fantasy text-amber-500">Create Character</h1>
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
        {/* Name Input */}
        <Card>
          <h2 className="text-lg font-bold text-slate-100 mb-4">Character Name</h2>
          <Input
            label="Name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (nameError) validateName(e.target.value);
            }}
            onBlur={() => validateName(name)}
            error={nameError}
            placeholder="Enter character name"
            maxLength={30}
            required
          />
        </Card>

        {/* Class Selection */}
        <Card>
          <h2 className="text-lg font-bold text-slate-100 mb-4">Choose Class</h2>
          <div className="grid gap-3">
            {classOptions.map((cls) => (
              <label
                key={cls.value}
                className={`
                  flex items-start gap-3 p-4 rounded-lg cursor-pointer
                  border transition-colors
                  ${
                    selectedClass === cls.value
                      ? 'bg-amber-900/30 border-amber-600'
                      : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                  }
                `}
              >
                <input
                  type="radio"
                  name="class"
                  value={cls.value}
                  checked={selectedClass === cls.value}
                  onChange={() => setSelectedClass(cls.value)}
                  className="mt-1 text-amber-500 focus:ring-amber-500"
                />
                <div>
                  <span className="font-medium text-slate-100">{cls.name}</span>
                  <p className="text-sm text-slate-400">{cls.description}</p>
                </div>
              </label>
            ))}
          </div>
        </Card>

        {/* Ability Scores */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-slate-100">Ability Scores</h2>
            <Button type="button" variant="secondary" onClick={handleRoll}>
              Roll 3d6
            </Button>
          </div>

          {abilities ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(abilities).map(([key, value]) => (
                <div
                  key={key}
                  className="bg-slate-900 rounded-lg p-4 text-center"
                >
                  <div className="text-2xl font-bold text-amber-500">{value}</div>
                  <div className="text-sm text-slate-400 capitalize">{key}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400 text-center py-8">
              Click &quot;Roll 3d6&quot; to generate your abilities
            </p>
          )}
        </Card>

        {/* Submit Button */}
        <Button
          type="submit"
          loading={submitting}
          disabled={!name || !abilities}
          className="w-full py-3 text-lg"
        >
          Create Character
        </Button>
      </form>
    </div>
  );
}
