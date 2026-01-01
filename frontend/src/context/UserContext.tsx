/**
 * User context provider component.
 * Implements anonymous sessions per ADR-005.
 */
import { useMemo, ReactNode } from 'react';
import { useLocalStorage } from '../hooks';
import { UserContext } from './userContextTypes';

/**
 * Generate a UUID v4 for anonymous user identification.
 */
function generateUserId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

interface UserProviderProps {
  children: ReactNode;
}

/**
 * Provides user identity and age verification state.
 */
export function UserProvider({ children }: UserProviderProps) {
  const [userId] = useLocalStorage<string>('chaos_user_id', generateUserId());
  const [ageVerified, setAgeVerified] = useLocalStorage<boolean>(
    'chaos_age_verified',
    false
  );

  const value = useMemo(
    () => ({ userId, ageVerified, setAgeVerified }),
    [userId, ageVerified, setAgeVerified]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}
