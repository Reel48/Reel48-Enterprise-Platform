import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('next/image', () => ({
  default: (props: Record<string, unknown>) => {
    const { fill, ...rest } = props;
    return <img {...rest} />;
  },
}));

vi.mock('@/hooks/useEngagement', () => ({
  useAddToWishlist: () => ({
    mutate: vi.fn((_data: unknown, opts?: { onSuccess?: () => void }) => {
      opts?.onSuccess?.();
    }),
    isPending: false,
  }),
  useRemoveFromWishlist: () => ({
    mutate: vi.fn((_id: unknown, opts?: { onSuccess?: () => void }) => {
      opts?.onSuccess?.();
    }),
    isPending: false,
  }),
}));

import { ProductCard } from '@/components/features/catalog/ProductCard';
import type { ProductCardProduct } from '@/components/features/catalog/ProductCard';

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

const mockProduct: ProductCardProduct = {
  id: 'prod-1',
  name: 'Premium Polo Shirt',
  sku: 'SKU-POLO-001',
  unitPrice: 29.99,
  imageUrls: [],
  sizes: ['S', 'M', 'L', 'XL'],
};

describe('ProductCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders product name, sku, and price', () => {
    render(<ProductCard product={mockProduct} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText('Premium Polo Shirt')).toBeInTheDocument();
    expect(screen.getByText('SKU: SKU-POLO-001')).toBeInTheDocument();
    expect(screen.getByText('$29.99')).toBeInTheDocument();
  });

  it('renders available sizes', () => {
    render(<ProductCard product={mockProduct} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText('Sizes: S, M, L, XL')).toBeInTheDocument();
  });

  it('shows outline heart when not wishlisted', () => {
    render(<ProductCard product={mockProduct} isWishlisted={false} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByRole('button', { name: /add to wishlist/i }),
    ).toBeInTheDocument();
  });

  it('shows filled heart when wishlisted', () => {
    render(
      <ProductCard
        product={mockProduct}
        isWishlisted={true}
        wishlistItemId="wl-1"
      />,
      { wrapper: createWrapper() },
    );

    expect(
      screen.getByRole('button', { name: /remove from wishlist/i }),
    ).toBeInTheDocument();
  });

  it('hides wishlist icon when showWishlist is false', () => {
    render(<ProductCard product={mockProduct} showWishlist={false} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.queryByRole('button', { name: /wishlist/i }),
    ).not.toBeInTheDocument();
  });

  it('shows toast on wishlist toggle', async () => {
    const user = userEvent.setup();
    render(<ProductCard product={mockProduct} isWishlisted={false} />, {
      wrapper: createWrapper(),
    });

    await user.click(
      screen.getByRole('button', { name: /add to wishlist/i }),
    );

    expect(screen.getByText('Added to wishlist')).toBeInTheDocument();
  });
});
