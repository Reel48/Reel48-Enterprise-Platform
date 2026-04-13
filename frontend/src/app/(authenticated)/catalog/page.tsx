'use client';

import { useState } from 'react';
import {
  Button,
  Dropdown,
  InlineNotification,
  Modal,
  NumberInput,
  Pagination,
  Search,
  Tag,
  Tile,
  ToastNotification,
} from '@carbon/react';
import { ArrowLeft, Catalog as CatalogIcon, Store } from '@carbon/react/icons';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

import { api } from '@/lib/api/client';
import { useCart } from '@/lib/cart/CartContext';
import { useHasRole } from '@/lib/auth/hooks';
import { StatusTag } from '@/components/ui/StatusTag';
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

interface CatalogProductApiEntry {
  id: string;
  catalogId: string;
  productId: string;
  displayOrder: number;
  priceOverride: number | null;
  product?: {
    id: string;
    name: string;
    description: string | null;
    sku: string;
    unitPrice: number;
    sizes: string[];
    decorationOptions: string[];
    imageUrls: string[];
    status: string;
  };
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
      if (!catalogId) return { data: [] as ProductCardProduct[], total: 0 };
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (search) {
        params.search = search;
      }
      const res = await api.get<CatalogProductApiEntry[]>(
        `/api/v1/catalogs/${catalogId}/products/`,
        params,
      );
      // Flatten nested product details into ProductCardProduct shape
      const products: ProductCardProduct[] = (res.data ?? [])
        .filter((cp) => cp.product)
        .map((cp) => ({
          id: cp.product!.id,
          name: cp.product!.name,
          sku: cp.product!.sku,
          unitPrice: cp.priceOverride ?? cp.product!.unitPrice,
          imageUrls: cp.product!.imageUrls,
          sizes: cp.product!.sizes,
          decorationOptions: cp.product!.decorationOptions,
          status: cp.product!.status,
        }));
      return {
        data: products,
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

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CatalogPage() {
  const canManageCatalogs = useHasRole(['corporate_admin', 'sub_brand_admin']);
  const [selectedCatalogId, setSelectedCatalogId] = useState<string | null>(null);
  const [productPage, setProductPage] = useState(1);
  const [productPerPage, setProductPerPage] = useState(20);
  const [search, setSearch] = useState('');

  // Cart modal state
  const [modalProduct, setModalProduct] = useState<ProductCardProduct | null>(null);
  const [modalSize, setModalSize] = useState<string | null>(null);
  const [modalDecoration, setModalDecoration] = useState<string | null>(null);
  const [modalQuantity, setModalQuantity] = useState(1);
  const [toast, setToast] = useState<string | null>(null);
  const [showCatalogWarning, setShowCatalogWarning] = useState(false);
  const [pendingProduct, setPendingProduct] = useState<ProductCardProduct | null>(null);

  const cart = useCart();

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

  // -------------------------------------------------------------------------
  // Cart modal handlers
  // -------------------------------------------------------------------------

  const openCartModal = (product: ProductCardProduct) => {
    if (selectedCatalogId && cart.catalogMismatch(selectedCatalogId)) {
      setPendingProduct(product);
      setShowCatalogWarning(true);
      return;
    }
    setModalProduct(product);
    setModalSize(product.sizes && product.sizes.length > 0 ? product.sizes[0] : null);
    setModalDecoration(
      product.decorationOptions && product.decorationOptions.length > 0
        ? product.decorationOptions[0]
        : null,
    );
    setModalQuantity(1);
  };

  const handleCatalogWarningConfirm = () => {
    cart.clearCart();
    setShowCatalogWarning(false);
    if (pendingProduct) {
      openCartModal(pendingProduct);
      setPendingProduct(null);
    }
  };

  const handleAddToCart = () => {
    if (!modalProduct || !selectedCatalogId || !selectedCatalog) return;

    cart.addItem(selectedCatalogId, selectedCatalog.name, {
      productId: modalProduct.id,
      productName: modalProduct.name,
      sku: modalProduct.sku,
      unitPrice: modalProduct.unitPrice,
      quantity: modalQuantity,
      size: modalSize,
      decoration: modalDecoration,
      imageUrl: modalProduct.imageUrls?.[0] ?? null,
    });

    setModalProduct(null);
    setToast(`${modalProduct.name} added to cart`);
    setTimeout(() => setToast(null), 3000);
  };

  // Catalog list view
  if (!selectedCatalogId) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-text-primary">
            Browse Catalogs
          </h1>
          {canManageCatalogs && (
            <Link href="/catalog/manage/catalogs">
              <Button kind="secondary" size="sm" renderIcon={Store}>
                Manage Catalogs
              </Button>
            </Link>
          )}
        </div>

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
                    <StatusTag type="purple">
                      Closes {formatDate(catalog.buyingWindowClosesAt)}
                    </StatusTag>
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
              onAddToCart={() => openCartModal(product)}
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

      {/* Add to Cart Modal */}
      <Modal
        open={modalProduct !== null}
        modalHeading="Add to Cart"
        primaryButtonText="Add to Cart"
        secondaryButtonText="Cancel"
        onRequestClose={() => setModalProduct(null)}
        onRequestSubmit={handleAddToCart}
        size="sm"
      >
        {modalProduct && (
          <div className="flex flex-col gap-4">
            <div>
              <h3 className="text-base font-semibold text-text-primary">
                {modalProduct.name}
              </h3>
              <p className="text-sm text-text-secondary">SKU: {modalProduct.sku}</p>
              <p className="text-lg font-semibold text-interactive mt-1">
                {formatPrice(modalProduct.unitPrice)}
              </p>
            </div>

            {modalProduct.sizes && modalProduct.sizes.length > 0 && (
              <Dropdown
                id="cart-size"
                titleText="Size"
                label="Select size"
                items={modalProduct.sizes.map((s) => ({ id: s, text: s }))}
                itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
                selectedItem={
                  modalSize
                    ? { id: modalSize, text: modalSize }
                    : null
                }
                onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) => {
                  setModalSize(selectedItem?.id ?? null);
                }}
              />
            )}

            {modalProduct.decorationOptions && modalProduct.decorationOptions.length > 0 && (
              <Dropdown
                id="cart-decoration"
                titleText="Decoration"
                label="Select decoration"
                items={modalProduct.decorationOptions.map((d) => ({ id: d, text: d }))}
                itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
                selectedItem={
                  modalDecoration
                    ? { id: modalDecoration, text: modalDecoration }
                    : null
                }
                onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) => {
                  setModalDecoration(selectedItem?.id ?? null);
                }}
              />
            )}

            <NumberInput
              id="cart-quantity"
              label="Quantity"
              min={1}
              max={100}
              value={modalQuantity}
              onChange={(_e: unknown, { value }: { value: number | string }) => {
                const num = typeof value === 'string' ? parseInt(value, 10) : value;
                if (!isNaN(num) && num >= 1) setModalQuantity(num);
              }}
            />
          </div>
        )}
      </Modal>

      {/* Catalog mismatch warning */}
      <Modal
        open={showCatalogWarning}
        modalHeading="Different catalog"
        primaryButtonText="Clear cart and continue"
        secondaryButtonText="Keep current cart"
        onRequestClose={() => {
          setShowCatalogWarning(false);
          setPendingProduct(null);
        }}
        onRequestSubmit={handleCatalogWarningConfirm}
        size="xs"
        danger
      >
        <p className="text-sm text-text-primary">
          Your cart has items from <strong>{cart.state.catalogName}</strong>. Adding
          items from this catalog will clear your existing cart.
        </p>
      </Modal>

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <ToastNotification
            kind="success"
            title={toast}
            timeout={3000}
            onCloseButtonClick={() => setToast(null)}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </div>
  );
}
