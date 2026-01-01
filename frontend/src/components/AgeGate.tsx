/**
 * Age verification gate component.
 * Implements ADR-007 for mature content.
 */
import { useUser } from '../context';
import { Button } from './ui/Button';
import { Card } from './ui/Card';

/**
 * Modal that appears on first visit for age verification.
 * Per ADR-007, users must confirm they are 18+ to access content.
 */
export function AgeGate() {
  const { ageVerified, setAgeVerified } = useUser();

  // Don't render if already verified
  if (ageVerified) {
    return null;
  }

  const handleYes = () => {
    setAgeVerified(true);
  };

  const handleNo = () => {
    window.location.href = 'https://google.com';
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <Card className="max-w-md text-center animate-fade-in">
        <h2 className="text-2xl font-fantasy text-amber-500 mb-4">
          Age Verification Required
        </h2>

        <div className="space-y-4 mb-6">
          <p className="text-slate-300">
            This game contains mature content including violence, dark themes,
            and intense fantasy scenarios.
          </p>
          <p className="text-slate-100 font-bold">
            Are you 18 years or older?
          </p>
        </div>

        <div className="flex gap-4 justify-center">
          <Button onClick={handleYes}>
            Yes, I am 18+
          </Button>
          <Button variant="secondary" onClick={handleNo}>
            No
          </Button>
        </div>
      </Card>
    </div>
  );
}
