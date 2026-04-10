'use client';

import { useState } from 'react';
import {
  Button,
  InlineNotification,
  Pagination,
  Search,
  Tag,
  Tile,
} from '@carbon/react';
import { ArrowLeft, Catalog as CatalogIcon } from '@carbon/react/icons';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { ProductCard } from '@/components/features/catalog/ProductCard';
import type { ProductCardProduct } from '@/components/features/catalog/ProductCard';
import type { Catalog } from '@/types/catalogs';

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useActiveCatalogs() {
  return useQuery({
    queryKey: ['catalogs-active'],
    queryFn: async () => {
      const res = await api.get<Catalog[]>('/api/v1/catalogs/', {
        status: 'active',
        page: '1',
        per_page: '100',
      });
      return res.data;
    },
  });
}

function useCatalogProducts(
  catalogId: string | null,
  page: number,
  perPage: number,
  search: string,
) {
  return useQuery({
    queryKey: ['catalog-products', catalogId, page, perPage, search],
    queryFn: async () => {
      if (!catalogId) return { data: [], total: 0 };
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (search) {
        params.search = search;
      }
      const res = await api.get<ProductCardProduct[]>(
        `/api/v1/catalogs/${catalogId}/products/`,
        params,
      );
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
    enabled: !!catalogId,
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateString: string | null): string {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CatalogPage() {
  const [selectedCatalogId, setSelectedCatalogId] = useState<string | null>(null);
  const [productPage, setProductPage] = useState(1);
  const [productPerPage, setProductPerPage] = useState(20);
  const [search, setSearch] = useState('');

  const { data: catalogs, isLoading: catalogsLoading, isError: catalogsError } = useActiveCatalogs();
  const { data: productsData, isLoading: productsLoading } = useCatalogProducts(
    selectedCatalogId,
    productPage,
    productPerPage,
    search,
  );

  const selectedCatalog = catalogs?.find((c) => c.id === selectedCatalogId);
  const products = productsData?.data ?? [];
  const productTotal = productsData?.total ?? 0;

  // Catalog list view
  if (!selectedCatalogId) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold text-text-primary">
          Browse Catalogs
        </h1>

        {catalogsError && (
          <InlineNotification
            kind="error"
            title="Failed to load catalogs"
            subtitle="Please try refreshing the page."
            hideCloseButton
          />
        )}

        {catalogsLoading ? (
          <div className="py-12 text-center text-text-secondary">
            Loading catalogs...
          </div>
        ) : !catalogs || catalogs.length === 0 ? (
          <Tile className="py-12 text-center">
            <CatalogIcon size={48} className="mx-auto mb-4 text-text-secondary" />
            <p className="text-lg font-medium text-text-primary">
              No active catalogs
            </p>
            <p className="text-sm text-text-secondary mt-1">
              Check back soon — new catalogs are added regularly
            </p>
          </Tile>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {catalogs.map((catalog) => (
              <Tile
                key={catalog.id}
                className="cursor-pointer hover:bg-layer-hover-01 transition-colors"
                onClick={() => {
                  setSelectedCatalogId(catalog.id);
                  setProductPage(1);
                  setSearch('');
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <CatalogIcon size={20} className="text-interactive" />
                  <h2 className="text-base font-semibold text-text-primary">
                    {catalog.name}
                  </h2>
                </div>
                {catalog.description && (
                  <p className="text-sm text-text-secondary mb-2 line-clamp-2">
                    {catalog.description}
                  </p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <Tag type="teal" size="sm">
                    {catalog.paymentModel === 'self_service' ? 'Self-Service' : 'Invoice'}
                  </Tag>
                  {catalog.paymentModel === 'invoice_after_close' && catalog.buyingWindowClosesAt && (
                    <Tag type="purple" size="sm">
                      Closes {formatDate(catalog.buyingWindowClosesAt)}
                    </Tag>
                  )}
                </div>
              </Tile>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Product grid view
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Button
          kind="ghost"
          size="sm"
          renderIcon={ArrowLeft}
          onClick={() => setSelectedCatalogId(null)}
        >
          Back to Catalogs
        </Button>
        <h1 className="text-2xl font-semibold text-text-primary">
          {selectedCatalog?.name ?? 'Catalog'}
        </h1>
      </div>

      <Search
        id="product-search"
        labelText="Search products"
        placeholder="Search by product name..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setProductPage(1);
        }}
        size="lg"
      />

      {productsLoading ? (
        <div className="py-12 text-center text-text-secondary">
          Loading products...
        </div>
      ) : products.length === 0 ? (
        <Tile className="py-12 text-center">
          <CatalogIcon size={48} className="mx-auto mb-4 text-text-secondary" />
          <p className="text-lg font-medium text-text-primary">
            {search ? 'No products match your search' : 'No products in this catalog'}
          </p>
          {search && (
            <p className="text-sm text-text-secondary mt-1">
              Try a different search term
            </p>
          )}
        </Tile>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              catalogId={selectedCatalogId}
              onAddToCart={() => {
                // TODO: Add to cart implementation when ordering flow is wired up
              }}
            />
          ))}
        </div>
      )}

      {productTotal > productPerPage && (
        <Pagination
          page={productPage}
          pageSize={productPerPage}
          pageSizes={[12, 20, 40]}
          totalItems={productTotal}
          onChange={({ page: newPage, pageSize }: { page: number; pageSize: number }) => {
            setProductPage(newPage);
            setProductPerPage(pageSize);
          }}
        />
      )}
    </div>
  );
}
