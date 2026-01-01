/**
 * Content card component.
 */
import { HTMLAttributes, forwardRef } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Add hover effect */
  hoverable?: boolean;
}

/**
 * Content container with dark fantasy styling.
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ hoverable, className = '', children, ...props }, ref) => {
    const baseStyles =
      'bg-slate-800 border border-slate-700 rounded-lg p-6';
    const hoverStyles = hoverable
      ? 'hover:border-amber-600 hover:shadow-lg transition-all cursor-pointer'
      : '';

    return (
      <div
        ref={ref}
        className={`${baseStyles} ${hoverStyles} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
