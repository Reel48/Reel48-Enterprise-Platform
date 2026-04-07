import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

const mockFetchAuthSession = vi.fn();

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => mockFetchAuthSession(...args),
}));

import { api, ApiRequestError } from '@/lib/api/client';

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

function mockAuthToken(token = 'test-id-token') {
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: { toString: () => token },
    },
  });
}

describe('API Client', () => {
  beforeEach(() => {
    mockAuthToken();
  });

  it('attaches the Authorization header with the ID token', async () => {
    let capturedAuth: string | null = null;
    server.use(
      http.get('http://localhost:8000/api/v1/test', ({ request }) => {
        capturedAuth = request.headers.get('Authorization');
        return HttpResponse.json({ data: { ok: true }, meta: {}, errors: [] });
      }),
    );

    await api.get('/api/v1/test');
    expect(capturedAuth).toBe('Bearer test-id-token');
  });

  it('transforms response keys from snake_case to camelCase', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/test', () => {
        return HttpResponse.json({
          data: { company_id: '123', sub_brand_id: '456' },
          meta: { per_page: 20 },
          errors: [],
        });
      }),
    );

    const response = await api.get<{ companyId: string; subBrandId: string }>(
      '/api/v1/test',
    );
    expect(response.data.companyId).toBe('123');
    expect(response.data.subBrandId).toBe('456');
  });

  it('transforms request body keys from camelCase to snake_case', async () => {
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post('http://localhost:8000/api/v1/test', async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ data: { id: '1' }, meta: {}, errors: [] }, { status: 201 });
      }),
    );

    await api.post('/api/v1/test', { companyId: '123', subBrandId: '456' });
    expect(capturedBody).toEqual({ company_id: '123', sub_brand_id: '456' });
  });

  it('retries once on 401 with a forced token refresh', async () => {
    let callCount = 0;
    server.use(
      http.get('http://localhost:8000/api/v1/test', () => {
        callCount++;
        if (callCount === 1) {
          return HttpResponse.json(
            { data: null, errors: [{ code: 'UNAUTHENTICATED', message: 'Token expired' }] },
            { status: 401 },
          );
        }
        return HttpResponse.json({ data: { ok: true }, meta: {}, errors: [] });
      }),
    );

    const response = await api.get('/api/v1/test');
    expect(callCount).toBe(2);
    expect(response.data).toEqual({ ok: true });
    expect(mockFetchAuthSession).toHaveBeenCalledWith({ forceRefresh: true });
  });

  it('throws ApiRequestError on non-2xx responses', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/test', () => {
        return HttpResponse.json(
          {
            data: null,
            errors: [{ code: 'NOT_FOUND', message: 'Resource not found' }],
          },
          { status: 404 },
        );
      }),
    );

    try {
      await api.get('/api/v1/test');
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiRequestError);
      const apiErr = err as ApiRequestError;
      expect(apiErr.status).toBe(404);
      expect(apiErr.errors[0].code).toBe('NOT_FOUND');
    }
  });

  it('handles 204 No Content responses', async () => {
    server.use(
      http.delete('http://localhost:8000/api/v1/test/1', () => {
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const response = await api.delete('/api/v1/test/1');
    expect(response.data).toBeNull();
    expect(response.errors).toEqual([]);
  });
});
