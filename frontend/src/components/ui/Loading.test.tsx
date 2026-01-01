/**
 * Tests for Loading component.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Loading } from './Loading';

describe('Loading', () => {
  it('renders spinner', () => {
    const { container } = render(<Loading />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders with message', () => {
    render(<Loading message="Loading data..." />);
    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('renders without message by default', () => {
    const { container } = render(<Loading />);
    expect(container.querySelector('p')).toBeNull();
  });

  it('applies correct size class for sm', () => {
    const { container } = render(<Loading size="sm" />);
    expect(container.querySelector('svg')).toHaveClass('h-4', 'w-4');
  });

  it('applies correct size class for md (default)', () => {
    const { container } = render(<Loading />);
    expect(container.querySelector('svg')).toHaveClass('h-8', 'w-8');
  });

  it('applies correct size class for lg', () => {
    const { container } = render(<Loading size="lg" />);
    expect(container.querySelector('svg')).toHaveClass('h-12', 'w-12');
  });
});
