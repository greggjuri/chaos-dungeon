/**
 * Hook to access user context.
 */
import { useContext } from 'react';
import { UserContext, UserContextValue } from './userContextTypes';

/**
 * Hook to access user context.
 * Must be used within UserProvider.
 */
export function useUser(): UserContextValue {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
}
