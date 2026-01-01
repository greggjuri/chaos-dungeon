/**
 * User context types and context creation.
 */
import { createContext } from 'react';

export interface UserContextValue {
  /** Anonymous user ID (UUID v4) */
  userId: string;
  /** Whether user has verified age (18+) */
  ageVerified: boolean;
  /** Set age verification status */
  setAgeVerified: (verified: boolean) => void;
}

export const UserContext = createContext<UserContextValue | null>(null);
