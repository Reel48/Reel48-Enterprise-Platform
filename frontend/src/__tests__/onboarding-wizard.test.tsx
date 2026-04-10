import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => '/onboarding',
}));

vi.mock('next/image', () => ({
  default: (props: Record<string, unknown>) => {
    const { fill, ...rest } = props;
    return <img {...rest} />;
  },
}));

vi.mock('@/lib/api/client', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: { onboardingComplete: true } }),
    delete: vi.fn(),
  },
}));

import { OnboardingWizard } from '@/components/features/engagement/OnboardingWizard';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('OnboardingWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all progress steps', () => {
    render(<OnboardingWizard />, { wrapper: createWrapper() });

    expect(screen.getByText('Welcome')).toBeInTheDocument();
    expect(screen.getByText('Sizing')).toBeInTheDocument();
    expect(screen.getByText('Delivery Address')).toBeInTheDocument();
    expect(screen.getByText('Department')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('shows welcome message on first step', () => {
    render(<OnboardingWizard companyName="Acme Corp" />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByText((content) => content.includes('Welcome to Acme Corp')),
    ).toBeInTheDocument();
  });

  it('navigates to next step on Next click', async () => {
    const user = userEvent.setup();
    render(<OnboardingWizard />, { wrapper: createWrapper() });

    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);

    // Should now be on sizing step
    expect(screen.getByText('Sizing Information')).toBeInTheDocument();
  });

  it('navigates back on Back click', async () => {
    const user = userEvent.setup();
    render(<OnboardingWizard />, { wrapper: createWrapper() });

    // Go to step 2
    await user.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Sizing Information')).toBeInTheDocument();

    // Go back
    await user.click(screen.getByRole('button', { name: /back/i }));
    expect(
      screen.getByText(/apparel program!/),
    ).toBeInTheDocument();
  });

  it('shows skip button on data entry steps', async () => {
    const user = userEvent.setup();
    render(<OnboardingWizard />, { wrapper: createWrapper() });

    // Go to sizing step
    await user.click(screen.getByRole('button', { name: /next/i }));

    expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument();
  });

  it('pre-fills profile data when provided', async () => {
    const user = userEvent.setup();
    render(
      <OnboardingWizard
        profile={{
          shirtSize: 'L',
          pantSize: '32x30',
          shoeSize: '10',
          deliveryAddressLine1: '123 Main St',
          deliveryAddressLine2: null,
          deliveryCity: 'Austin',
          deliveryState: 'TX',
          deliveryZip: '78701',
          deliveryCountry: 'US',
          department: 'Engineering',
          jobTitle: 'Developer',
          onboardingComplete: false,
        }}
      />,
      { wrapper: createWrapper() },
    );

    // Navigate to address step
    await user.click(screen.getByRole('button', { name: /next/i }));
    await user.click(screen.getByRole('button', { name: /next/i }));

    // Check address pre-filled
    const addressInput = screen.getByLabelText('Address Line 1');
    expect(addressInput).toHaveValue('123 Main St');
  });

  it('shows Finish Setup button on last step', async () => {
    const user = userEvent.setup();
    render(<OnboardingWizard />, { wrapper: createWrapper() });

    // Navigate through all steps
    for (let i = 0; i < 4; i++) {
      const btn =
        screen.queryByRole('button', { name: /next/i }) ??
        screen.queryByRole('button', { name: /skip/i });
      if (btn) await user.click(btn);
    }

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /finish setup/i }),
      ).toBeInTheDocument();
    });
  });
});
