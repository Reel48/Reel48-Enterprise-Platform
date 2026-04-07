import { render, screen, act, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockGetCurrentUser = vi.fn();
const mockFetchAuthSession = vi.fn();
const mockSignIn = vi.fn();
const mockSignOut = vi.fn();

vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  fetchAuthSession: (...args: unknown[]) => mockFetchAuthSession(...args),
  signIn: (...args: unknown[]) => mockSignIn(...args),
  signOut: (...args: unknown[]) => mockSignOut(...args),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => '/dashboard',
}));

import { AuthProvider } from '@/lib/auth/context';
import { useAuth } from '@/lib/auth/hooks';

function TestConsumer() {
  const { user, authState, isAuthenticated } = useAuth();
  return (
    <div>
      <span data-testid="auth-state">{authState}</span>
      <span data-testid="is-authenticated">{String(isAuthenticated)}</span>
      {user && (
        <>
          <span data-testid="user-email">{user.email}</span>
          <span data-testid="user-role">{user.tenantContext.role}</span>
          <span data-testid="company-id">{user.tenantContext.companyId ?? 'null'}</span>
          <span data-testid="sub-brand-id">{user.tenantContext.subBrandId ?? 'null'}</span>
        </>
      )}
    </div>
  );
}

function mockAuthenticatedSession(overrides?: {
  role?: string;
  companyId?: string | null;
  subBrandId?: string | null;
}) {
  const role = overrides?.role ?? 'employee';
  const companyId = overrides && 'companyId' in overrides ? overrides.companyId : 'comp-123';
  const subBrandId = overrides && 'subBrandId' in overrides ? overrides.subBrandId : 'sb-456';

  mockGetCurrentUser.mockResolvedValue({ userId: 'user-001' });
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: {
        toString: () => 'mock-token',
        payload: {
          email: 'test@example.com',
          name: 'Test User',
          'custom:company_id': companyId,
          'custom:sub_brand_id': subBrandId,
          'custom:role': role,
        },
      },
    },
  });
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts in loading state', () => {
    mockGetCurrentUser.mockReturnValue(new Promise(() => {}));
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    expect(screen.getByTestId('auth-state').textContent).toBe('loading');
  });

  it('sets authenticated state when a valid session exists', async () => {
    mockAuthenticatedSession();

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state').textContent).toBe('authenticated');
    });

    expect(screen.getByTestId('is-authenticated').textContent).toBe('true');
    expect(screen.getByTestId('user-email').textContent).toBe('test@example.com');
    expect(screen.getByTestId('user-role').textContent).toBe('employee');
    expect(screen.getByTestId('company-id').textContent).toBe('comp-123');
    expect(screen.getByTestId('sub-brand-id').textContent).toBe('sb-456');
  });

  it('sets unauthenticated state when no session exists', async () => {
    mockGetCurrentUser.mockRejectedValue(new Error('No user'));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state').textContent).toBe('unauthenticated');
    });

    expect(screen.getByTestId('is-authenticated').textContent).toBe('false');
  });

  it('extracts tenant context for corporate_admin with null sub_brand_id', async () => {
    mockAuthenticatedSession({
      role: 'corporate_admin',
      companyId: 'comp-789',
      subBrandId: null,
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('user-role').textContent).toBe('corporate_admin');
    });

    expect(screen.getByTestId('company-id').textContent).toBe('comp-789');
    expect(screen.getByTestId('sub-brand-id').textContent).toBe('null');
  });

  it('extracts tenant context for reel48_admin with null company_id and sub_brand_id', async () => {
    mockAuthenticatedSession({
      role: 'reel48_admin',
      companyId: null,
      subBrandId: null,
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('user-role').textContent).toBe('reel48_admin');
    });

    expect(screen.getByTestId('company-id').textContent).toBe('null');
    expect(screen.getByTestId('sub-brand-id').textContent).toBe('null');
  });

  it('clears state on signOut', async () => {
    mockAuthenticatedSession();
    mockSignOut.mockResolvedValue(undefined);

    function TestWithLogout() {
      const { user, authState, signOut } = useAuth();
      return (
        <div>
          <span data-testid="auth-state">{authState}</span>
          {user && <span data-testid="user-email">{user.email}</span>}
          <button onClick={signOut}>Logout</button>
        </div>
      );
    }

    render(
      <AuthProvider>
        <TestWithLogout />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state').textContent).toBe('authenticated');
    });

    await act(async () => {
      screen.getByRole('button', { name: 'Logout' }).click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('auth-state').textContent).toBe('unauthenticated');
    });

    expect(screen.queryByTestId('user-email')).toBeNull();
  });
});
