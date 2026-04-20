import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
  usePathname: () => '/register',
}));

const mockApiPost = vi.fn();

vi.mock('@/lib/api/client', () => ({
  api: {
    post: (...args: unknown[]) => mockApiPost(...args),
    get: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  ApiRequestError: class ApiRequestError extends Error {
    status: number;
    errors: Array<{ code: string; message: string }>;
    constructor(status: number, errors: Array<{ code: string; message: string }>) {
      super(errors[0]?.message || 'Error');
      this.name = 'ApiRequestError';
      this.status = status;
      this.errors = errors;
    }
  },
}));

import { AuthProvider } from '@/lib/auth/context';
import RegisterPage from '@/app/(public)/register/page';
import { ApiRequestError } from '@/lib/api/client';

function renderRegisterPage() {
  mockGetCurrentUser.mockRejectedValue(new Error('No user'));
  return render(
    <AuthProvider>
      <RegisterPage />
    </AuthProvider>,
  );
}

const registerSuccessResponse = {
  data: {
    message: 'Registration successful. Please check your email to verify your account.',
  },
  meta: {},
  errors: [],
};

describe('Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all single-step fields', async () => {
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('shows password mismatch error without calling API', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Full Name'), 'Test User');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'different456');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });

    expect(mockApiPost).not.toHaveBeenCalled();
  });

  it('calls /auth/register with all fields and shows success message', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost.mockResolvedValueOnce(registerSuccessResponse);

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Full Name'), 'Test User');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/registration successful/i)).toBeInTheDocument();
    });

    expect(mockApiPost).toHaveBeenCalledWith(
      '/api/v1/auth/register',
      {
        code: 'REEL7K3M',
        email: 'test@example.com',
        fullName: 'Test User',
        password: 'password123',
      },
      { skipAuth: true },
    );
    expect(screen.getByText(/sign in to your account/i)).toBeInTheDocument();
  });

  it('shows error notification on registration failure', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost.mockRejectedValueOnce(
      new ApiRequestError(400, [{ code: 'REGISTRATION_FAILED', message: 'Registration failed' }]),
    );

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Full Name'), 'Test User');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/registration failed/i)).toBeInTheDocument();
    });
  });

  it('has link to login page', async () => {
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText(/already have an account/i)).toBeInTheDocument();
    });
  });
});
