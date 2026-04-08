import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockGetCurrentUser = vi.fn();
const mockFetchAuthSession = vi.fn();
const mockSignIn = vi.fn();
const mockSignOut = vi.fn();

const mockPush = vi.fn();

vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  fetchAuthSession: (...args: unknown[]) => mockFetchAuthSession(...args),
  signIn: (...args: unknown[]) => mockSignIn(...args),
  signOut: (...args: unknown[]) => mockSignOut(...args),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: mockPush }),
  usePathname: () => '/invite',
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
import InviteLandingPage from '@/app/(public)/invite/page';
import InviteRegisterPage from '@/app/(public)/invite/[token]/page';
import { ApiRequestError } from '@/lib/api/client';

const registerSuccessResponse = {
  data: {
    message: 'Registration successful. Please check your email to verify your account.',
  },
  meta: {},
  errors: [],
};

describe('Invite Landing Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCurrentUser.mockRejectedValue(new Error('No user'));
  });

  it('renders invite token input and continue button', async () => {
    render(
      <AuthProvider>
        <InviteLandingPage />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Invite Token')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /continue/i })).toBeInTheDocument();
  });

  it('navigates to /invite/[token] on submit', async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <InviteLandingPage />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Invite Token')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Invite Token'), 'abc123token');
    await user.click(screen.getByRole('button', { name: /continue/i }));

    expect(mockPush).toHaveBeenCalledWith('/invite/abc123token');
  });

  it('has link to login page', async () => {
    render(
      <AuthProvider>
        <InviteLandingPage />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/already have an account/i)).toBeInTheDocument();
    });
  });
});

describe('Invite Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCurrentUser.mockRejectedValue(new Error('No user'));
  });

  function renderInvitePage(token = 'test-invite-token-123') {
    return render(
      <AuthProvider>
        <InviteRegisterPage params={{ token }} />
      </AuthProvider>,
    );
  }

  it('renders registration form with email, name, and password fields', async () => {
    renderInvitePage();

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('shows password mismatch error without calling API', async () => {
    const user = userEvent.setup();
    renderInvitePage();

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

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

  it('shows success message with login link on successful registration', async () => {
    const user = userEvent.setup();
    renderInvitePage();

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    mockApiPost.mockResolvedValue(registerSuccessResponse);

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Full Name'), 'Test User');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/registration successful/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/sign in to your account/i)).toBeInTheDocument();
  });

  it('shows error notification on invalid or expired invite token', async () => {
    const user = userEvent.setup();
    renderInvitePage();

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    mockApiPost.mockRejectedValue(
      new ApiRequestError(400, [{ code: 'REGISTRATION_FAILED', message: 'Registration failed' }]),
    );

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Full Name'), 'Test User');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/this invite link is invalid or has expired/i)).toBeInTheDocument();
    });
  });

  it('has link to login page', async () => {
    renderInvitePage();

    await waitFor(() => {
      expect(screen.getByText(/already have an account/i)).toBeInTheDocument();
    });
  });
});
