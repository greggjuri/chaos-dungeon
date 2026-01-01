/**
 * Tests for API service.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { request, getUserId } from './api';
import { ApiRequestError } from '../types';

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

describe('API Service', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('chaos_user_id', JSON.stringify('test-user-id'));
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getUserId', () => {
    it('returns user ID from localStorage', () => {
      expect(getUserId()).toBe('test-user-id');
    });

    it('throws error when user ID not found', () => {
      localStorage.clear();
      expect(() => getUserId()).toThrow('User ID not found');
    });
  });

  describe('request', () => {
    it('includes X-User-Id header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: 'test' }),
      });

      await request('/test');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-User-Id': 'test-user-id',
          }),
        })
      );
    });

    it('includes Content-Type header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });

      await request('/test');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('returns parsed JSON for successful response', async () => {
      const responseData = { id: 1, name: 'test' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(responseData),
      });

      const result = await request('/test');
      expect(result).toEqual(responseData);
    });

    it('returns undefined for 204 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const result = await request('/test');
      expect(result).toBeUndefined();
    });

    it('throws ApiRequestError on non-2xx response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: 'Not found' }),
      });

      await expect(request('/test')).rejects.toThrow(ApiRequestError);
    });

    it('includes error details in ApiRequestError', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ error: 'Bad request', details: { field: 'name' } }),
      });

      try {
        await request('/test');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiRequestError);
        expect((error as ApiRequestError).status).toBe(400);
        expect((error as ApiRequestError).error).toBe('Bad request');
        expect((error as ApiRequestError).details).toEqual({ field: 'name' });
      }
    });

    it('handles failed JSON parse on error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      await expect(request('/test')).rejects.toThrow(ApiRequestError);
    });

    it('passes through request options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });

      await request('/test', {
        method: 'POST',
        body: JSON.stringify({ data: 'test' }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ data: 'test' }),
        })
      );
    });
  });
});
