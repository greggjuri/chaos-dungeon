/**
 * Tests for UserContext.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { UserProvider } from './UserContext';
import { useUser } from './useUser';

function TestComponent() {
  const { userId, ageVerified, setAgeVerified } = useUser();
  return (
    <div>
      <span data-testid="user-id">{userId}</span>
      <span data-testid="age-verified">{String(ageVerified)}</span>
      <button onClick={() => setAgeVerified(true)}>Verify Age</button>
    </div>
  );
}

describe('UserContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('provides a user ID', () => {
    render(
      <UserProvider>
        <TestComponent />
      </UserProvider>
    );

    const userId = screen.getByTestId('user-id').textContent;
    expect(userId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  });

  it('persists user ID across renders', () => {
    const { rerender } = render(
      <UserProvider>
        <TestComponent />
      </UserProvider>
    );

    const firstUserId = screen.getByTestId('user-id').textContent;

    rerender(
      <UserProvider>
        <TestComponent />
      </UserProvider>
    );

    const secondUserId = screen.getByTestId('user-id').textContent;
    expect(firstUserId).toBe(secondUserId);
  });

  it('starts with ageVerified as false', () => {
    render(
      <UserProvider>
        <TestComponent />
      </UserProvider>
    );

    expect(screen.getByTestId('age-verified').textContent).toBe('false');
  });

  it('allows setting age verification', () => {
    render(
      <UserProvider>
        <TestComponent />
      </UserProvider>
    );

    act(() => {
      screen.getByRole('button', { name: 'Verify Age' }).click();
    });

    expect(screen.getByTestId('age-verified').textContent).toBe('true');
  });

  it('throws error when useUser is used outside provider', () => {
    // Suppress console error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => render(<TestComponent />)).toThrow(
      'useUser must be used within UserProvider'
    );

    consoleSpy.mockRestore();
  });
});
