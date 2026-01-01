/**
 * Tests for NotFoundPage component.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { NotFoundPage } from './NotFoundPage';

function renderNotFoundPage() {
  return render(
    <BrowserRouter>
      <NotFoundPage />
    </BrowserRouter>
  );
}

describe('NotFoundPage', () => {
  it('renders 404 heading', () => {
    renderNotFoundPage();
    expect(screen.getByText('404')).toBeInTheDocument();
  });

  it('renders descriptive message', () => {
    renderNotFoundPage();
    expect(screen.getByText(/lost in the dungeon/i)).toBeInTheDocument();
  });

  it('has link back to home', () => {
    renderNotFoundPage();
    const link = screen.getByRole('link', { name: /return to safety/i });
    expect(link).toHaveAttribute('href', '/');
  });
});
