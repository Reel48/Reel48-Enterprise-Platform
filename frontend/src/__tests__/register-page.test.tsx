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

const validOrgCodeResponse = {
  data: {
    companyName: 'Acme Corp',
    subBrands: [
      { id: 'sb-1', name: 'North Division', slug: 'north-division', isDefault: true },
      { id: 'sb-2', name: 'South Division', slug: 'south-division', isDefault: false },
    ],
  },
  meta: {},
  errors: [],
};

const singleSubBrandResponse = {
  data: {
    companyName: 'Small Co',
    subBrands: [
      { id: 'sb-only', name: 'Main', slug: 'main', isDefault: true },
    ],
  },
  meta: {},
  errors: [],
};

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

  it('renders org code input and validate button', async () => {
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /validate code/i })).toBeInTheDocument();
  });

  it('shows error notification on invalid org code', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost.mockRejectedValue(
      new ApiRequestError(400, [{ code: 'INVALID_REQUEST', message: 'Invalid registration code' }]),
    );

    await user.type(screen.getByLabelText('Organization Code'), 'BADCODE1');
    await user.click(screen.getByRole('button', { name: /validate code/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid registration code/i)).toBeInTheDocument();
    });
  });

  it('transitions to step 2 on valid org code and shows company name', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost.mockResolvedValue(validOrgCodeResponse);

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.click(screen.getByRole('button', { name: /validate code/i }));

    await waitFor(() => {
      expect(screen.getByText(/registering with acme corp/i)).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
  });

  it('pre-selects the default sub-brand in the dropdown', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost.mockResolvedValue(validOrgCodeResponse);

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.click(screen.getByRole('button', { name: /validate code/i }));

    await waitFor(() => {
      expect(screen.getByText('North Division')).toBeInTheDocument();
    });
  });

  it('hides sub-brand dropdown when only one sub-brand exists', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost.mockResolvedValue(singleSubBrandResponse);

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.click(screen.getByRole('button', { name: /validate code/i }));

    await waitFor(() => {
      expect(screen.getByText(/registering with small co/i)).toBeInTheDocument();
    });

    expect(screen.queryByText('Select your location')).not.toBeInTheDocument();
  });

  it('shows password mismatch error without calling API', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost.mockResolvedValue(validOrgCodeResponse);

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.click(screen.getByRole('button', { name: /validate code/i }));

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

    // Only the validate-org-code call should have been made, not the register call
    expect(mockApiPost).toHaveBeenCalledTimes(1);
  });

  it('shows success message with login link on successful registration', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost
      .mockResolvedValueOnce(validOrgCodeResponse)
      .mockResolvedValueOnce(registerSuccessResponse);

    // Step 1
    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.click(screen.getByRole('button', { name: /validate code/i }));

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    // Step 2
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

  it('shows error notification on registration failure', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByLabelText('Organization Code')).toBeInTheDocument();
    });

    mockApiPost
      .mockResolvedValueOnce(validOrgCodeResponse)
      .mockRejectedValueOnce(
        new ApiRequestError(400, [{ code: 'REGISTRATION_FAILED', message: 'Registration failed' }]),
      );

    await user.type(screen.getByLabelText('Organization Code'), 'REEL7K3M');
    await user.click(screen.getByRole('button', { name: /validate code/i }));

    await waitFor(() => {
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

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
