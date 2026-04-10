import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/wishlist',
}));

vi.mock('next/image', () => ({
  default: (props: Record<string, unknown>) => {
    const { fill, ...rest } = props;
    return <img {...rest} />;
  },
}));

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiDelete = vi.fn();
vi.mock('@/lib/api/client', () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: (...args: unknown[]) => mockApiDelete(...args),
  },
}));

import WishlistPage from '@/app/(authenticated)/wishlist/page';

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

const mockWishlistItems = [
  {
    id: 'wl-1',
    productId: 'prod-1',
    productName: 'Classic Polo Shirt',
    productSku: 'SKU-POLO-001',
    productUnitPrice: 49.99,
    productImageUrl: '/images/polo.jpg',
    productStatus: 'active',
    isPurchasable: true,
    notes: 'Need size L',
    createdAt: '2026-04-01T10:00:00Z',
  },
  {
    id: 'wl-2',
    productId: 'prod-2',
    productName: 'Safety Vest',
    productSku: 'SKU-VEST-002',
    productUnitPrice: 29.99,
    productImageUrl: null,
    productStatus: 'active',
    isPurchasable: true,
    notes: null,
    createdAt: '2026-03-30T14:00:00Z',
  },
  {
    id: 'wl-3',
    productId: 'prod-3',
    productName: 'Winter Jacket',
    productSku: 'SKU-JACK-003',
    productUnitPrice: 89.99,
    productImageUrl: '/images/jacket.jpg',
    productStatus: 'archived',
    isPurchasable: false,
    notes: null,
    createdAt: '2026-03-28T12:00:00Z',
  },
];

describe('WishlistPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders wishlist items with product details', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Classic Polo Shirt')).toBeInTheDocument();
    });

    expect(screen.getByText('Safety Vest')).toBeInTheDocument();
    expect(screen.getByText('Winter Jacket')).toBeInTheDocument();
  });

  it('shows item count in header', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('3 items')).toBeInTheDocument();
    });
  });

  it('displays product prices', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('$49.99')).toBeInTheDocument();
    });

    expect(screen.getByText('$29.99')).toBeInTheDocument();
    expect(screen.getByText('$89.99')).toBeInTheDocument();
  });

  it('shows SKU for each item', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('SKU: SKU-POLO-001')).toBeInTheDocument();
    });
  });

  it('shows Unavailable tag for non-purchasable items', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Unavailable')).toBeInTheDocument();
    });
  });

  it('shows notes when present', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/Need size L/)).toBeInTheDocument();
    });
  });

  it('shows empty state when wishlist is empty', async () => {
    mockApiGet.mockResolvedValue({
      data: [],
      meta: { page: 1, perPage: 20, total: 0 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Your wishlist is empty')).toBeInTheDocument();
    });

    expect(
      screen.getByText('Browse catalogs to find products you love'),
    ).toBeInTheDocument();
  });

  it('renders Remove buttons for each item', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      const removeButtons = screen.getAllByRole('button', { name: /remove/i });
      expect(removeButtons).toHaveLength(3);
    });
  });

  it('calls remove API when Remove button is clicked', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });
    mockApiDelete.mockResolvedValue({ data: null, meta: {}, errors: [] });

    const user = userEvent.setup();
    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Classic Polo Shirt')).toBeInTheDocument();
    });

    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    await user.click(removeButtons[0]);

    await waitFor(() => {
      expect(mockApiDelete).toHaveBeenCalledWith('/api/v1/wishlists/wl-1');
    });
  });

  it('shows Browse Catalogs button', async () => {
    mockApiGet.mockResolvedValue({
      data: mockWishlistItems,
      meta: { page: 1, perPage: 20, total: 3 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Classic Polo Shirt')).toBeInTheDocument();
    });

    // Header Browse Catalogs button
    const browseButtons = screen.getAllByRole('link', { name: /browse catalogs/i });
    expect(browseButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('shows page heading', async () => {
    mockApiGet.mockResolvedValue({
      data: [],
      meta: { page: 1, perPage: 20, total: 0 },
      errors: [],
    });

    render(<WishlistPage />, { wrapper: createWrapper() });

    expect(screen.getByText('My Wishlist')).toBeInTheDocument();
  });
});
