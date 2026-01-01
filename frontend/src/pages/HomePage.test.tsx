/**
 * Tests for HomePage component.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { HomePage } from './HomePage';

function renderHomePage() {
  return render(
    <BrowserRouter>
      <HomePage />
    </BrowserRouter>
  );
}

describe('HomePage', () => {
  it('renders the game title', () => {
    renderHomePage();
    expect(screen.getByRole('heading', { name: /chaos dungeon/i })).toBeInTheDocument();
  });

  it('renders the tagline', () => {
    renderHomePage();
    expect(screen.getByText(/epic text-based rpg adventure/i)).toBeInTheDocument();
  });

  it('has start adventure button', () => {
    renderHomePage();
    expect(screen.getByRole('link', { name: /start your adventure/i })).toBeInTheDocument();
  });

  it('links to characters page', () => {
    renderHomePage();
    const link = screen.getByRole('link', { name: /start your adventure/i });
    expect(link).toHaveAttribute('href', '/characters');
  });

  it('displays feature highlights', () => {
    renderHomePage();
    // Use getByRole for headings in feature cards to avoid matching tagline text
    expect(screen.getByRole('heading', { name: /ai dungeon master/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /classic d&d rules/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /persistent world/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /dark fantasy/i })).toBeInTheDocument();
  });

  it('has create character CTA', () => {
    renderHomePage();
    expect(screen.getByRole('link', { name: /create your character/i })).toBeInTheDocument();
  });
});
