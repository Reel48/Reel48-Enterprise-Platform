'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Button, Tile, ToastNotification } from '@carbon/react';
import { Favorite, FavoriteFilled, Catalog } from '@carbon/react/icons';

import {
  useAddToWishlist,
  useRemoveFromWishlist,
} from '@/hooks/useEngagement';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ProductCardProduct {
  id: string;
  name: string;
  sku: string;
  unitPrice: number;
  imageUrls?: string[];
  sizes?: string[];
  status?: string;
}

interface ProductCardProps {
  product: ProductCardProduct;
  catalogId?: string;
  isWishlisted?: boolean;
  wishlistItemId?: string;
  onAddToCart?: (productId: string) => void;
  showWishlist?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ProductCard({
  product,
  catalogId,
  isWishlisted = false,
  wishlistItemId,
  onAddToCart,
  showWishlist = true,
}: ProductCardProps) {
  const addToWishlist = useAddToWishlist();
  const removeFromWishlist = useRemoveFromWishlist();
  const [toast, setToast] = useState<{ kind: 'success'; message: string } | null>(null);

  const imageUrl = product.imageUrls?.[0] ?? null;

  const handleWishlistToggle = () => {
    if (isWishlisted && wishlistItemId) {
      removeFromWishlist.mutate(wishlistItemId, {
        onSuccess: () => {
          setToast({ kind: 'success', message: 'Removed from wishlist' });
          setTimeout(() => setToast(null), 3000);
        },
      });
    } else {
      addToWishlist.mutate(
        { productId: product.id, catalogId },
        {
          onSuccess: () => {
            setToast({ kind: 'success', message: 'Added to wishlist' });
            setTimeout(() => setToast(null), 3000);
          },
        },
      );
    }
  };

  const isWishlistLoading =
    addToWishlist.isPending || removeFromWishlist.isPending;

  return (
    <>
      <Tile className="flex flex-col h-full relative">
        {/* Wishlist heart icon */}
        {showWishlist && (
          <button
            onClick={handleWishlistToggle}
            disabled={isWishlistLoading}
            className="absolute top-3 right-3 z-10 flex items-center justify-center w-8 h-8 rounded-full bg-white/80 hover:bg-white transition-colors disabled:opacity-50"
            aria-label={
              isWishlisted ? 'Remove from wishlist' : 'Add to wishlist'
            }
          >
            {isWishlisted ? (
              <FavoriteFilled size={20} className="text-interactive" />
            ) : (
              <Favorite size={20} className="text-text-secondary" />
            )}
          </button>
        )}

        {/* Product image */}
        {imageUrl ? (
          <div className="relative w-full h-40 bg-layer-02 rounded mb-3 overflow-hidden">
            <Image
              src={imageUrl}
              alt={product.name}
              fill
              className="object-cover"
            />
          </div>
        ) : (
          <div className="w-full h-40 bg-layer-02 rounded mb-3 flex items-center justify-center">
            <Catalog size={32} className="text-text-secondary" />
          </div>
        )}

        {/* Product info */}
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-text-primary line-clamp-2 mb-1">
            {product.name}
          </h3>
          <p className="text-xs text-text-secondary mb-1">SKU: {product.sku}</p>
          <p className="text-lg font-semibold text-interactive mb-2">
            {formatPrice(product.unitPrice)}
          </p>
          {product.sizes && product.sizes.length > 0 && (
            <p className="text-xs text-text-secondary">
              Sizes: {product.sizes.join(', ')}
            </p>
          )}
        </div>

        {/* Add to cart */}
        {onAddToCart && (
          <Button
            kind="primary"
            size="sm"
            onClick={() => onAddToCart(product.id)}
            className="mt-3 w-full"
          >
            Add to Cart
          </Button>
        )}
      </Tile>

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <ToastNotification
            kind="success"
            title={toast.message}
            timeout={3000}
            onCloseButtonClick={() => setToast(null)}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </>
  );
}
