import { render, screen, waitFor } from '@testing-library/react';
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
          'custom:sub_brand_id':
            role === 'reel48_admin' || role === 'corporate_admin' ? null : 'sb-456',
          'custom:role': role,
        },
      },
    },
  });
}

function renderSidebar(role: string) {
  mockAuthenticatedSession(role);
  return render(
    <AuthProvider>
      <Sidebar />
    </AuthProvider>,
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

    expect(screen.getByText('Catalog')).toBeInTheDocument();
    expect(screen.getByText('Orders')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.queryByText('Bulk Orders')).not.toBeInTheDocument();
    expect(screen.queryByText('Approvals')).not.toBeInTheDocument();
  });

  it('shows bulk orders and approvals for regional_manager', async () => {
    renderSidebar('regional_manager');

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Bulk Orders')).toBeInTheDocument();
    expect(screen.getByText('Approvals')).toBeInTheDocument();
  });

  it('shows users and brand settings for sub_brand_admin', async () => {
    renderSidebar('sub_brand_admin');

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Brand Settings')).toBeInTheDocument();
    expect(screen.getByText('Bulk Orders')).toBeInTheDocument();
  });

  it('shows analytics and invoices for corporate_admin', async () => {
    renderSidebar('corporate_admin');

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Invoices')).toBeInTheDocument();
    expect(screen.getByText('All Sub-Brands')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
  });

  it('shows platform-specific nav for reel48_admin', async () => {
    renderSidebar('reel48_admin');

    await waitFor(() => {
      expect(screen.getByText('Platform Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Companies')).toBeInTheDocument();
    expect(screen.getByText('Catalogs')).toBeInTheDocument();
    expect(screen.getByText('Invoices')).toBeInTheDocument();

    // Should NOT show tenant nav items
    expect(screen.queryByText('Profile')).not.toBeInTheDocument();
    expect(screen.queryByText('Orders')).not.toBeInTheDocument();
  });
});
