import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders the application title', () => {
    render(<App />);
    expect(screen.getByText('Chaos Dungeon')).toBeInTheDocument();
  });

  it('renders the welcome message', () => {
    render(<App />);
    expect(screen.getByText('Welcome, Adventurer')).toBeInTheDocument();
  });

  it('displays game feature list', () => {
    render(<App />);
    expect(screen.getByText(/Create your character/)).toBeInTheDocument();
    expect(screen.getByText(/Explore procedurally generated dungeons/)).toBeInTheDocument();
  });

  it('shows the footer with credits', () => {
    render(<App />);
    expect(screen.getByText(/Powered by Claude AI/)).toBeInTheDocument();
    expect(screen.getByText(/BECMI D&D Rules/)).toBeInTheDocument();
  });
});
