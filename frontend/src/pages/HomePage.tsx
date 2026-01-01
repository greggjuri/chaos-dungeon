/**
 * Landing page component.
 */
import { Link } from 'react-router-dom';
import { Button, Card } from '../components';

const features = [
  {
    title: 'AI Dungeon Master',
    description: 'Experience dynamic storytelling powered by Claude AI.',
  },
  {
    title: 'Classic D&D Rules',
    description: 'Based on BECMI (1983) for authentic gameplay.',
  },
  {
    title: 'Persistent World',
    description: 'Your choices matter. NPCs remember. Consequences persist.',
  },
  {
    title: 'Dark Fantasy',
    description: 'Mature themes, intense combat, and epic adventures.',
  },
];

/**
 * Landing page with hero section and feature highlights.
 */
export function HomePage() {
  return (
    <div className="max-w-4xl mx-auto space-y-12">
      {/* Hero Section */}
      <section className="text-center py-12 space-y-6">
        <h1 className="text-5xl md:text-6xl font-fantasy text-amber-500">
          Chaos Dungeon
        </h1>
        <p className="text-xl text-slate-300 max-w-2xl mx-auto">
          Embark on an epic text-based RPG adventure where an AI Dungeon Master
          crafts your unique story. Create your hero, explore dangerous dungeons,
          and forge your legend.
        </p>
        <Link to="/characters">
          <Button className="text-lg px-8 py-3">
            Start Your Adventure
          </Button>
        </Link>
      </section>

      {/* Features Grid */}
      <section className="grid md:grid-cols-2 gap-6">
        {features.map((feature) => (
          <Card key={feature.title}>
            <h3 className="text-lg font-bold text-amber-500 mb-2">
              {feature.title}
            </h3>
            <p className="text-slate-400">
              {feature.description}
            </p>
          </Card>
        ))}
      </section>

      {/* Call to Action */}
      <section className="text-center py-8">
        <Card className="inline-block">
          <p className="text-slate-300 mb-4">
            Ready to face the darkness?
          </p>
          <Link to="/characters">
            <Button>Create Your Character</Button>
          </Link>
        </Card>
      </section>
    </div>
  );
}
