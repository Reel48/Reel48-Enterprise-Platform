import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
  usePathname: () => '/login',
}));

vi.mock('@/lib/api/client', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: null, meta: {}, errors: [] }),
  },
}));

import { AuthProvider } from '@/lib/auth/context';
import LoginPage from '@/app/(public)/login/page';

function renderLoginPage() {
  mockGetCurrentUser.mockRejectedValue(new Error('No user'));
  return render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>,
  );
}

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the login form with email and password fields', async () => {
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows an error notification on failed sign-in', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    mockSignIn.mockRejectedValue(new Error('Incorrect username or password'));

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/Incorrect username or password/i)).toBeInTheDocument();
    });
  });

  it('redirects to /dashboard on successful sign-in', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    mockSignIn.mockResolvedValue({ isSignedIn: true });
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

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Password'), 'correctpassword');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('shows links to register and invite pages', async () => {
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByText(/register with an org code/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/have an invite/i)).toBeInTheDocument();
  });
});
