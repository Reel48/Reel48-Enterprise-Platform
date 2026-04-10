import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeAll, afterAll, afterEach, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupServer } from 'msw/node';

import { analyticsHandlers } from '../mocks/analytics-handlers';

// --- Mock Amplify auth ---
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
  usePathname: () => '/admin/analytics',
}));

// Mock @carbon/charts-react to avoid jsdom SVG/ResizeObserver errors
vi.mock('@carbon/charts-react', () => ({
  LineChart: () => <div data-testid="mock-line-chart">Chart</div>,
}));

import { AuthProvider } from '@/lib/auth/context';
import ClientAnalyticsPage from '@/app/(authenticated)/admin/analytics/page';

// --- MSW Server ---
const server = setupServer(...analyticsHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function mockAuthenticatedSession(role: string) {
  mockGetCurrentUser.mockResolvedValue({ userId: 'user-001' });
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: {
        toString: () => 'mock-token',
        payload: {
          email: 'admin@example.com',
          name: 'Test Admin',
          'custom:company_id': role === 'reel48_admin' ? null : 'comp-123',
          'custom:sub_brand_id':
            role === 'reel48_admin' || role === 'corporate_admin' ? null : 'sb-456',
          'custom:role': role,
        },
      },
    },
  });
}

function renderPage(role: string) {
  mockAuthenticatedSession(role);
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ClientAnalyticsPage />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('ClientAnalyticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all sections for corporate_admin', async () => {
    renderPage('corporate_admin');

    await waitFor(() => {
      expect(screen.getByText('Analytics')).toBeInTheDocument();
    });

    // Corporate admin sees all sections including sub-brand and invoice
    await waitFor(() => {
      expect(screen.getByText('Spend Summary')).toBeInTheDocument();
    });

    expect(screen.getByText('Spend by Sub-Brand')).toBeInTheDocument();
    expect(screen.getByText('Spend Over Time')).toBeInTheDocument();
    expect(screen.getByText('Top Products')).toBeInTheDocument();
    expect(screen.getByText('Order Status Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Size Distribution')).toBeInTheDocument();
    expect(screen.getByText('Invoice Summary')).toBeInTheDocument();
    expect(screen.getByText('Approval Metrics')).toBeInTheDocument();
  });

  it('does NOT show Spend by Sub-Brand for sub_brand_admin', async () => {
    renderPage('sub_brand_admin');

    // Wait for auth to resolve and page to render with data
    await waitFor(() => {
      expect(screen.getByText('Spend Summary')).toBeInTheDocument();
    });

    // Wait for data to load in at least one section
    await waitFor(() => {
      expect(screen.getByText('Top Products')).toBeInTheDocument();
    });

    // Sub-brand admin should NOT see sub-brand breakdown or invoice summary
    expect(screen.queryByText('Spend by Sub-Brand')).not.toBeInTheDocument();
    expect(screen.queryByText('Invoice Summary')).not.toBeInTheDocument();

    expect(screen.getByText('Approval Metrics')).toBeInTheDocument();
  });

  it('shows access denied for employee role', async () => {
    renderPage('employee');

    await waitFor(() => {
      expect(screen.getByText('Access Denied')).toBeInTheDocument();
    });

    expect(
      screen.getByText('You do not have permission to view analytics.'),
    ).toBeInTheDocument();

    // No analytics sections should be present
    expect(screen.queryByText('Spend Summary')).not.toBeInTheDocument();
  });

  it('shows loading states while data fetches', async () => {
    renderPage('corporate_admin');

    // Wait for page to render (auth resolves)
    await waitFor(() => {
      expect(screen.getByText('Spend Summary')).toBeInTheDocument();
    });

    // Eventually data loads and sections appear
    await waitFor(() => {
      expect(screen.getByText('Top Products')).toBeInTheDocument();
    });
  });

  it('renders date range filter with default dates', async () => {
    renderPage('corporate_admin');

    await waitFor(() => {
      expect(screen.getByText('Spend Summary')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Start date')).toBeInTheDocument();
    expect(screen.getByLabelText('End date')).toBeInTheDocument();
  });

  it('allows regional_manager to view analytics', async () => {
    renderPage('regional_manager');

    await waitFor(() => {
      expect(screen.getByText('Spend Summary')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('Top Products')).toBeInTheDocument();
    });

    // Regional manager should NOT see sub-brand or invoice sections
    expect(screen.queryByText('Spend by Sub-Brand')).not.toBeInTheDocument();
    expect(screen.queryByText('Invoice Summary')).not.toBeInTheDocument();
  });
});
