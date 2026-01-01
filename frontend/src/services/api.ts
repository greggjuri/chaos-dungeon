/**
 * Base API client with error handling.
 */
import { ApiRequestError } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

/**
 * Get the user ID from localStorage.
 * @throws Error if user ID not found
 */
export function getUserId(): string {
  const stored = localStorage.getItem('chaos_user_id');
  if (stored) {
    return JSON.parse(stored) as string;
  }
  throw new Error('User ID not found');
}

/**
 * Make an API request with automatic user ID header.
 *
 * @param path - API endpoint path
 * @param options - Fetch options
 * @returns Parsed JSON response
 * @throws ApiRequestError on non-2xx responses
 */
export async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const userId = getUserId();

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': userId,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new ApiRequestError(response.status, error.error, error.details);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
