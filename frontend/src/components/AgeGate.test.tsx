/**
 * Tests for AgeGate component.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserProvider } from '../context';
import { AgeGate } from './AgeGate';

// Wrapper with UserProvider
function renderWithProvider() {
  return render(
    <UserProvider>
      <AgeGate />
    </UserProvider>
  );
}

describe('AgeGate', () => {
  beforeEach(() => {
    localStorage.clear();
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    });
  });

  it('renders modal when not verified', () => {
    renderWithProvider();
    expect(screen.getByText('Age Verification Required')).toBeInTheDocument();
  });

  it('does not render when already verified', () => {
    localStorage.setItem('chaos_age_verified', 'true');
    renderWithProvider();
    expect(screen.queryByText('Age Verification Required')).not.toBeInTheDocument();
  });

  it('shows age verification question', () => {
    renderWithProvider();
    expect(screen.getByText('Are you 18 years or older?')).toBeInTheDocument();
  });

  it('has Yes and No buttons', () => {
    renderWithProvider();
    expect(screen.getByRole('button', { name: /yes/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /no/i })).toBeInTheDocument();
  });

  it('dismisses modal and stores verification on Yes click', async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /yes/i }));
    });

    expect(screen.queryByText('Age Verification Required')).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem('chaos_age_verified')!)).toBe(true);
  });

  it('redirects away on No click', async () => {
    const user = userEvent.setup();
    renderWithProvider();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /no/i }));
    });

    expect(window.location.href).toBe('https://google.com');
  });

  it('mentions mature content', () => {
    renderWithProvider();
    expect(screen.getByText(/mature content/i)).toBeInTheDocument();
  });
});
