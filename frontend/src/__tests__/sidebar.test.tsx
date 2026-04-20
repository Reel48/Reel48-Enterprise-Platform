import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

vi.mock('@/lib/api/client', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: null, meta: {}, errors: [] }),
  },
}));

import { AuthProvider } from '@/lib/auth/context';
import { Sidebar } from '@/components/layout/Sidebar';

function mockAuthenticatedSession(role: string) {
  mockGetCurrentUser.mockResolvedValue({ userId: 'user-001' });
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: {
        toString: () => 'mock-token',
        payload: {
          email: 'test@example.com',
          name: 'Test User',
          'custom:company_id': role === 'reel48_admin' ? null : 'comp-123',
          'custom:role': role,
        },
      },
    },
  });
}

function renderSidebar(role: string) {
  mockAuthenticatedSession(role);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Sidebar />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows basic nav items for employee role', async () => {
    renderSidebar('employee');

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Products')).toBeInTheDocument();
    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.queryByText('Users')).not.toBeInTheDocument();
    expect(screen.queryByText('Analytics')).not.toBeInTheDocument();
  });

  it('shows same minimal nav for manager role', async () => {
    renderSidebar('manager');

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Products')).toBeInTheDocument();
    expect(screen.queryByText('Users')).not.toBeInTheDocument();
  });

  it('shows users, analytics, and company settings for company_admin', async () => {
    renderSidebar('company_admin');

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Company Settings')).toBeInTheDocument();
  });

  it('shows platform-specific nav for reel48_admin', async () => {
    renderSidebar('reel48_admin');

    await waitFor(() => {
      expect(screen.getByText('Platform Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Companies')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();

    expect(screen.queryByText('Profile')).not.toBeInTheDocument();
    expect(screen.queryByText('Products')).not.toBeInTheDocument();
  });
});
