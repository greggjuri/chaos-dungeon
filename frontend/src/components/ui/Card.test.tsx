/**
 * Tests for Card component.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card } from './Card';

describe('Card', () => {
  it('renders children correctly', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies base styles', () => {
    render(<Card>Content</Card>);
    const card = screen.getByText('Content').closest('div');
    expect(card).toHaveClass('bg-slate-800');
    expect(card).toHaveClass('rounded-lg');
  });

  it('applies hoverable styles when hoverable prop is true', () => {
    render(<Card hoverable>Hoverable</Card>);
    const card = screen.getByText('Hoverable').closest('div');
    expect(card).toHaveClass('hover:border-amber-600');
    expect(card).toHaveClass('cursor-pointer');
  });

  it('does not apply hoverable styles by default', () => {
    render(<Card>Not hoverable</Card>);
    const card = screen.getByText('Not hoverable').closest('div');
    expect(card).not.toHaveClass('cursor-pointer');
  });

  it('applies custom className', () => {
    render(<Card className="custom-class">Custom</Card>);
    const card = screen.getByText('Custom').closest('div');
    expect(card).toHaveClass('custom-class');
  });
});
