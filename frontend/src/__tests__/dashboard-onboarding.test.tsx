import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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

vi.mock('next/image', () => ({
  default: (props: Record<string, unknown>) => {
    const { fill, ...rest } = props;
    return <img {...rest} />;
  },
}));

// Mock API responses
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
vi.mock('@/lib/api/client', () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn(),
  },
}));

import { AuthProvider } from '@/lib/auth/context';
import DashboardPage from '@/app/(authenticated)/dashboard/page';

function mockAuthenticatedSession() {
  mockGetCurrentUser.mockResolvedValue({ userId: 'user-001' });
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: {
        toString: () => 'mock-token',
        payload: {
          email: 'test@example.com',
          name: 'Test User',
          'custom:company_id': 'comp-123',
          'custom:role': 'employee',
        },
      },
    },
  });
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    );
  };
}

describe('Dashboard onboarding banner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthenticatedSession();
  });

  it('shows onboarding banner when onboarding_complete is false', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url === '/api/v1/profiles/me') {
        return Promise.resolve({
          data: { onboardingComplete: false, shirtSize: null, pantSize: null, shoeSize: null, deliveryAddressLine1: null, department: null, jobTitle: null },
          meta: {},
          errors: [],
        });
      }
      // Default empty list responses
      return Promise.resolve({ data: [], meta: { page: 1, perPage: 20, total: 0 }, errors: [] });
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Get Started')).toBeInTheDocument();
    });
  });

  it('does not show onboarding banner when onboarding_complete is true', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url === '/api/v1/profiles/me') {
        return Promise.resolve({
          data: { onboardingComplete: true, shirtSize: 'M', pantSize: null, shoeSize: null, deliveryAddressLine1: null, department: 'Eng', jobTitle: null },
          meta: {},
          errors: [],
        });
      }
      return Promise.resolve({ data: [], meta: { page: 1, perPage: 20, total: 0 }, errors: [] });
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Welcome back/)).toBeInTheDocument();
    });

    expect(screen.queryByText('Get Started')).not.toBeInTheDocument();
  });
});
