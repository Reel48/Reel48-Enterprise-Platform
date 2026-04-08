import { fetchAuthSession } from 'aws-amplify/auth';

import type { ApiError, ApiResponse } from '@/types/api';
import { camelToSnake, deepTransformKeys, snakeToCamel } from './transform';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiRequestError extends Error {
  public errors: ApiError[];
  public status: number;

  constructor(status: number, errors: ApiError[]) {
    const message = errors[0]?.message || `Request failed with status ${status}`;
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.errors = errors;
  }
}

async function getAuthToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() ?? null;
  } catch {
    return null;
  }
}

async function refreshAndGetToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession({ forceRefresh: true });
    return session.tokens?.idToken?.toString() ?? null;
  } catch {
    return null;
  }
}

interface FetchOptions {
  body?: unknown;
  params?: Record<string, string>;
  skipAuth?: boolean;
}

async function fetchWithAuth<T>(
  method: string,
  url: string,
  options?: FetchOptions,
  isRetry = false,
): Promise<ApiResponse<T>> {
  const token = options?.skipAuth
    ? null
    : isRetry
      ? await refreshAndGetToken()
      : await getAuthToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let fullUrl = `${BASE_URL}${url}`;
  if (options?.params) {
    const searchParams = new URLSearchParams(options.params);
    fullUrl += `?${searchParams.toString()}`;
  }

  const fetchInit: RequestInit = {
    method,
    headers,
  };

  if (options?.body !== undefined) {
    fetchInit.body = JSON.stringify(
      deepTransformKeys(options.body, camelToSnake),
    );
  }

  const response = await fetch(fullUrl, fetchInit);

  if (response.status === 401 && !isRetry && !options?.skipAuth) {
    return fetchWithAuth<T>(method, url, options, true);
  }

  if (response.status === 204) {
    return { data: null as T, meta: {}, errors: [] };
  }

  const rawJson = await response.json();
  const transformed = deepTransformKeys<ApiResponse<T>>(rawJson, snakeToCamel);

  if (!response.ok) {
    throw new ApiRequestError(response.status, transformed.errors || []);
  }

  return transformed;
}

export const api = {
  get: <T>(url: string, params?: Record<string, string>, options?: { skipAuth?: boolean }) =>
    fetchWithAuth<T>('GET', url, { params, ...options }),

  post: <T>(url: string, body?: unknown, options?: { skipAuth?: boolean }) =>
    fetchWithAuth<T>('POST', url, { body, ...options }),

  put: <T>(url: string, body?: unknown, options?: { skipAuth?: boolean }) =>
    fetchWithAuth<T>('PUT', url, { body, ...options }),

  patch: <T>(url: string, body?: unknown, options?: { skipAuth?: boolean }) =>
    fetchWithAuth<T>('PATCH', url, { body, ...options }),

  delete: <T>(url: string, options?: { skipAuth?: boolean }) =>
    fetchWithAuth<T>('DELETE', url, options),
};
