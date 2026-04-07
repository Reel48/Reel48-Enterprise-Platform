import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockGetCurrentUser = vi.fn();
const mockFetchAuthSession = vi.fn();
const mockSignIn = vi.fn();
const mockSignOut = vi.fn();

const mockReplace = vi.fn();

vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  fetchAuthSession: (...args: unknown[]) => mockFetchAuthSession(...args),
  signIn: (...args: unknown[]) => mockSignIn(...args),
  signOut: (...args: unknown[]) => mockSignOut(...args),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  usePathname: () => '/dashboard',
}));

import { AuthProvider } from '@/lib/auth/context';
import { ProtectedRoute } from '@/components/features/auth/ProtectedRoute';

function mockAuthenticatedSession(role = 'employee') {
  mockGetCurrentUser.mockResolvedValue({ userId: 'user-001' });
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: {
        toString: () => 'mock-token',
        payload: {
          email: 'test@example.com',
          name: 'Test User',
          'custom:company_id': 'comp-123',
          'custom:sub_brand_id': 'sb-456',
          'custom:role': role,
        },
      },
    },
  });
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while checking authentication', () => {
    mockGetCurrentUser.mockReturnValue(new Promise(() => {}));

    render(
      <AuthProvider>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </AuthProvider>,
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects to /login when unauthenticated', async () => {
    mockGetCurrentUser.mockRejectedValue(new Error('No user'));

    render(
      <AuthProvider>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login');
    });
  });

  it('renders children when authenticated', async () => {
    mockAuthenticatedSession();

    render(
      <AuthProvider>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
  });

  it('shows access denied when user role is not in requiredRoles', async () => {
    mockAuthenticatedSession('employee');

    render(
      <AuthProvider>
        <ProtectedRoute requiredRoles={['corporate_admin', 'reel48_admin']}>
          <div>Admin Content</div>
        </ProtectedRoute>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Access Denied')).toBeInTheDocument();
    });

    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
  });

  it('renders children when user role matches requiredRoles', async () => {
    mockAuthenticatedSession('corporate_admin');

    render(
      <AuthProvider>
        <ProtectedRoute requiredRoles={['corporate_admin', 'reel48_admin']}>
          <div>Admin Content</div>
        </ProtectedRoute>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Admin Content')).toBeInTheDocument();
    });
  });
});
