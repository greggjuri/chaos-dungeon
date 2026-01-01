/**
 * Tests for GamePage component.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { GamePage } from './GamePage';

function renderGamePage(sessionId: string) {
  return render(
    <MemoryRouter initialEntries={[`/play/${sessionId}`]}>
      <Routes>
        <Route path="/play/:sessionId" element={<GamePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('GamePage', () => {
  it('renders game session heading', () => {
    renderGamePage('test-session-123');
    expect(screen.getByRole('heading', { name: /game session/i })).toBeInTheDocument();
  });

  it('displays session ID from URL', () => {
    renderGamePage('abc-123-def');
    expect(screen.getByText('abc-123-def')).toBeInTheDocument();
  });

  it('shows placeholder message', () => {
    renderGamePage('test-session');
    expect(screen.getByText(/game ui coming/i)).toBeInTheDocument();
  });

  it('has link back to characters', () => {
    renderGamePage('test-session');
    const link = screen.getByRole('link', { name: /back to characters/i });
    expect(link).toHaveAttribute('href', '/characters');
  });
});
