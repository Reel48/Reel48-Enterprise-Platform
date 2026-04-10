import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeAll, afterAll, afterEach, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupServer } from 'msw/node';

import { analyticsHandlers } from '../mocks/analytics-handlers';

// --- Mock Amplify auth ---
const mockGetCurrentUser = vi.fn();
const mockFetchAuthSession = vi.fn();

vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  fetchAuthSession: (...args: unknown[]) => mockFetchAuthSession(...args),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => '/platform/analytics',
}));

// Mock @carbon/charts-react to avoid jsdom SVG/ResizeObserver errors
vi.mock('@carbon/charts-react', () => ({
  LineChart: () => <div data-testid="mock-line-chart">Chart</div>,
}));

import PlatformAnalyticsPage from '@/app/(platform)/platform/analytics/page';

// --- MSW Server ---
const server = setupServer(...analyticsHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function mockPlatformAdminSession() {
  mockGetCurrentUser.mockResolvedValue({ userId: 'admin-001' });
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: {
        toString: () => 'mock-platform-token',
        payload: {
          email: 'platform@reel48.com',
          name: 'Platform Admin',
          'custom:company_id': null,
          'custom:sub_brand_id': null,
          'custom:role': 'reel48_admin',
        },
      },
    },
  });
}

function renderPage() {
  mockPlatformAdminSession();
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <PlatformAnalyticsPage />
    </QueryClientProvider>,
  );
}

describe('PlatformAnalyticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders platform overview cards', async () => {
    renderPage();

    expect(screen.getByText('Platform Analytics')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Platform Overview')).toBeInTheDocument();
    });

    // Check overview card values from mock data
    await waitFor(() => {
      expect(screen.getByText('Total Companies')).toBeInTheDocument();
    });

    // 15 appears for both "Total Companies" and revenue table "Invoice Count" for Tech Solutions
    expect(screen.getAllByText('15').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Total Sub-Brands')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Total Users')).toBeInTheDocument();
    expect(screen.getByText('3,500')).toBeInTheDocument();
    expect(screen.getByText('Total Orders')).toBeInTheDocument();
    expect(screen.getByText('12,000')).toBeInTheDocument();
    expect(screen.getByText('$450,000.00')).toBeInTheDocument();
    expect(screen.getByText('Active Catalogs')).toBeInTheDocument();
  });

  it('shows revenue by company table', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Revenue by Company')).toBeInTheDocument();
    });

    // Table data from mock
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    expect(screen.getByText('Global Industries')).toBeInTheDocument();
    expect(screen.getByText('Tech Solutions')).toBeInTheDocument();
    expect(screen.getByText('$150,000.00')).toBeInTheDocument();
  });

  it('renders all platform analytics sections', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Platform Overview')).toBeInTheDocument();
    });

    expect(screen.getByText('Revenue by Company')).toBeInTheDocument();
    expect(screen.getByText('Revenue Over Time')).toBeInTheDocument();
    expect(screen.getByText('Order Status Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Top Products (Platform-Wide)')).toBeInTheDocument();
    expect(screen.getByText('Invoice Summary')).toBeInTheDocument();
    expect(screen.getByText('Approval Metrics')).toBeInTheDocument();
  });

  it('renders date range filter', async () => {
    renderPage();

    expect(screen.getByLabelText('Start date')).toBeInTheDocument();
    expect(screen.getByLabelText('End date')).toBeInTheDocument();
  });
});
