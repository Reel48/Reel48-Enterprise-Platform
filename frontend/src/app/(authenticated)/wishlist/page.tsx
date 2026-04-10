'use client';

import { useState } from 'react';
import Image from 'next/image';
import {
  Button,
  Pagination,
  Tag,
  Tile,
} from '@carbon/react';
import { TrashCan, FavoriteFilled, Catalog } from '@carbon/react/icons';

import { useWishlist, useRemoveFromWishlist } from '@/hooks/useEngagement';
import type { WishlistItem } from '@/types/engagement';

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

function WishlistCard({ item, onRemove }: { item: WishlistItem; onRemove: () => void }) {
  const isAvailable = item.productStatus === 'active' && item.isPurchasable;

  return (
    <Tile className="flex flex-col h-full">
      <div className="flex-1">
        {item.productImageUrl ? (
          <div className="relative w-full h-40 bg-layer-02 rounded mb-3 overflow-hidden">
            <Image
              src={item.productImageUrl}
              alt={item.productName}
              fill
              className="object-cover"
            />
          </div>
        ) : (
          <div className="w-full h-40 bg-layer-02 rounded mb-3 flex items-center justify-center">
            <Catalog size={32} className="text-text-secondary" />
          </div>
        )}

        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="text-sm font-semibold text-text-primary line-clamp-2">
            {item.productName}
          </h3>
          {!isAvailable && (
            <Tag type="red" size="sm">
              Unavailable
            </Tag>
          )}
        </div>

        <p className="text-xs text-text-secondary mb-1">
          SKU: {item.productSku}
        </p>

        <p className="text-lg font-semibold text-interactive mb-2">
          {formatPrice(item.productUnitPrice)}
        </p>

        {item.notes && (
          <p className="text-xs text-text-secondary italic mb-2 line-clamp-2">
            &ldquo;{item.notes}&rdquo;
          </p>
        )}
      </div>

      <Button
        kind="danger--ghost"
        size="sm"
        onClick={onRemove}
        renderIcon={TrashCan}
        className="mt-2"
      >
        Remove
      </Button>
    </Tile>
  );
}

export default function WishlistPage() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const { data, isLoading } = useWishlist({ page, perPage });
  const removeFromWishlist = useRemoveFromWishlist();

  const items = data?.data ?? [];
  const total = data?.meta?.total ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">
            My Wishlist
          </h1>
          {total > 0 && (
            <p className="text-sm text-text-secondary mt-1">
              {total} item{total !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <Button kind="primary" size="sm" href="/catalog">
          Browse Catalogs
        </Button>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-text-secondary">
          Loading wishlist...
        </div>
      ) : items.length === 0 ? (
        <Tile className="py-12 text-center">
          <FavoriteFilled size={48} className="mx-auto mb-4 text-text-secondary" />
          <p className="text-lg font-medium text-text-primary">
            Your wishlist is empty
          </p>
          <p className="text-sm text-text-secondary mt-1 mb-4">
            Browse catalogs to find products you love
          </p>
          <Button kind="primary" size="sm" href="/catalog">
            Browse Catalogs
          </Button>
        </Tile>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((item) => (
            <WishlistCard
              key={item.id}
              item={item}
              onRemove={() => removeFromWishlist.mutate(item.id)}
            />
          ))}
        </div>
      )}

      {total > perPage && (
        <Pagination
          page={page}
          pageSize={perPage}
          pageSizes={[12, 20, 40]}
          totalItems={total}
          onChange={({ page: newPage, pageSize }: { page: number; pageSize: number }) => {
            setPage(newPage);
            setPerPage(pageSize);
          }}
        />
      )}
    </div>
  );
}
