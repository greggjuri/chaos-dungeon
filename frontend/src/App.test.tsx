/**
 * Tests for App component.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    localStorage.clear();
    // Pre-verify age to skip age gate in most tests
    localStorage.setItem('chaos_age_verified', 'true');
    localStorage.setItem('chaos_user_id', JSON.stringify('test-user'));
  });

  it('renders the application title in header', async () => {
    await act(async () => {
      render(<App />);
    });
    // Header has a span inside an anchor, HomePage has h1 - use getAllBy and check at least one exists
    const elements = screen.getAllByText('Chaos Dungeon');
    expect(elements.length).toBeGreaterThan(0);
  });

  it('renders the home page by default', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByRole('heading', { name: /chaos dungeon/i, level: 1 })).toBeInTheDocument();
  });

  it('shows the footer with credits', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByText(/Powered by Claude AI/)).toBeInTheDocument();
  });

  it('shows age gate when not verified', async () => {
    localStorage.clear();
    localStorage.setItem('chaos_user_id', JSON.stringify('test-user'));

    await act(async () => {
      render(<App />);
    });

    expect(screen.getByText('Age Verification Required')).toBeInTheDocument();
  });

  it('shows navigation links when age verified', async () => {
    await act(async () => {
      render(<App />);
    });

    expect(screen.getByRole('link', { name: /characters/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /new game/i })).toBeInTheDocument();
  });
});
