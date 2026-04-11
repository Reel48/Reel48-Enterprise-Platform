'use client';

import { useState, useEffect, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  DataTable,
  InlineNotification,
  Loading,
  Modal,
  NumberInput,
  Pagination,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  TextArea,
  TextInput,
  ToastNotification,
} from '@carbon/react';
import {
  Add,
  Catalog,
  Edit,
  SendFilled,
  TrashCan,
} from '@carbon/react/icons';
import { ComboBox } from '@carbon/react';

import { useAuth, useHasRole } from '@/lib/auth/hooks';
import { StatusTag } from '@/components/ui/StatusTag';
import type { Product } from '@/types/products';
import type { CatalogStatus, PaymentModel } from '@/types/catalogs';
import { useProducts } from '../../_hooks';
import {
  useCatalog,
  useCatalogProducts,
  useAddCatalogProduct,
  useRemoveCatalogProduct,
  useSubmitCatalog,
  useUpdateCatalog,
} from '../_hooks';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

const currencyFmt = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

const STATUS_TAG_COLOR: Record<CatalogStatus, 'gray' | 'blue' | 'teal' | 'green' | 'red' | 'purple'> = {
  draft: 'gray',
  submitted: 'blue',
  approved: 'teal',
  active: 'green',
  closed: 'purple',
  archived: 'red',
};

function paymentModelLabel(model: PaymentModel): string {
  return model === 'self_service' ? 'Self-Service' : 'Invoice After Close';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CatalogDetailPage() {
  const params = useParams();
  const router = useRouter();
  const catalogId = params.id as string;
  const { user } = useAuth();
  const isAdmin = useHasRole(['sub_brand_admin', 'corporate_admin', 'reel48_admin']);

  useEffect(() => {
    if (user && !isAdmin) {
      router.replace('/catalog');
    }
  }, [user, isAdmin, router]);

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  // Add product
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [addDisplayOrder, setAddDisplayOrder] = useState<number | string>(0);
  const [addPriceOverride, setAddPriceOverride] = useState<number | string>('');

  // Remove product
  const [removeProductId, setRemoveProductId] = useState<string | null>(null);

  // Edit catalog
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');

  // Submit confirmation
  const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false);

  // Products pagination for the ComboBox source
  const [productSearchPage] = useState(1);

  // ---------------------------------------------------------------------------
  // Data hooks
  // ---------------------------------------------------------------------------

  const { data: catalog, isLoading: catalogLoading } = useCatalog(catalogId);
  const { data: catalogProductsData, isLoading: productsLoading } = useCatalogProducts(catalogId);
  const { data: allProductsData } = useProducts(productSearchPage, 100, 'active');

  const addCatalogProduct = useAddCatalogProduct();
  const removeCatalogProduct = useRemoveCatalogProduct();
  const submitCatalog = useSubmitCatalog();
  const updateCatalog = useUpdateCatalog();

  const catalogProducts = catalogProductsData?.data ?? [];
  const allProducts = allProductsData?.data ?? [];

  const isDraft = catalog?.status === 'draft';

  // Build lookup of product details by product ID
  const productMap = useMemo(() => {
    const map = new Map<string, Product>();
    for (const p of allProducts) {
      map.set(p.id, p);
    }
    return map;
  }, [allProducts]);

  // Products available to add (not already in catalog)
  const catalogProductIds = useMemo(
    () => new Set(catalogProducts.map((cp) => cp.productId)),
    [catalogProducts],
  );

  const availableProducts = useMemo(
    () => allProducts.filter((p) => !catalogProductIds.has(p.id)),
    [allProducts, catalogProductIds],
  );

  // ---------------------------------------------------------------------------
  // Toast
  // ---------------------------------------------------------------------------

  function showToast(kind: 'success' | 'error', message: string) {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  function handleAddProduct() {
    if (!selectedProduct) return;
    const displayOrder =
      typeof addDisplayOrder === 'string' ? parseInt(addDisplayOrder, 10) : addDisplayOrder;
    const priceOverride =
      addPriceOverride === '' ? undefined : typeof addPriceOverride === 'string'
        ? parseFloat(addPriceOverride)
        : addPriceOverride;

    addCatalogProduct.mutate(
      {
        catalogId,
        data: {
          productId: selectedProduct.id,
          displayOrder: isNaN(displayOrder) ? 0 : displayOrder,
          priceOverride: priceOverride !== undefined && !isNaN(priceOverride) ? priceOverride : undefined,
        },
      },
      {
        onSuccess: () => {
          showToast('success', `Added "${selectedProduct.name}" to catalog`);
          setAddModalOpen(false);
          setSelectedProduct(null);
          setAddDisplayOrder(0);
          setAddPriceOverride('');
        },
        onError: () => {
          showToast('error', 'Failed to add product');
        },
      },
    );
  }

  function handleRemoveProduct() {
    if (!removeProductId) return;
    removeCatalogProduct.mutate(
      { catalogId, productId: removeProductId },
      {
        onSuccess: () => {
          showToast('success', 'Product removed from catalog');
          setRemoveProductId(null);
        },
        onError: () => {
          showToast('error', 'Failed to remove product');
          setRemoveProductId(null);
        },
      },
    );
  }

  function handleSubmit() {
    submitCatalog.mutate(catalogId, {
      onSuccess: () => {
        showToast('success', 'Catalog submitted for approval');
        setSubmitConfirmOpen(false);
      },
      onError: (err) => {
        showToast('error', err.message || 'Failed to submit catalog');
        setSubmitConfirmOpen(false);
      },
    });
  }

  function openEditModal() {
    if (!catalog) return;
    setEditName(catalog.name);
    setEditDescription(catalog.description ?? '');
    setEditOpen(true);
  }

  function handleUpdate() {
    if (!editName.trim()) return;
    updateCatalog.mutate(
      {
        id: catalogId,
        data: {
          name: editName.trim(),
          description: editDescription.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          showToast('success', 'Catalog updated');
          setEditOpen(false);
        },
        onError: () => {
          showToast('error', 'Failed to update catalog');
        },
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Guard
  // ---------------------------------------------------------------------------

  if (!user || !isAdmin) return null;

  if (catalogLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loading withOverlay={false} description="Loading catalog..." />
      </div>
    );
  }

  if (!catalog) {
    return (
      <InlineNotification
        kind="error"
        title="Catalog not found"
        subtitle="The catalog you're looking for doesn't exist."
        hideCloseButton
      />
    );
  }

  // ---------------------------------------------------------------------------
  // Products DataTable
  // ---------------------------------------------------------------------------

  const productTableHeaders = [
    { key: 'name', header: 'Product Name' },
    { key: 'sku', header: 'SKU' },
    { key: 'price', header: 'Price' },
    { key: 'displayOrder', header: 'Display Order' },
    { key: 'actions', header: '' },
  ];

  const productTableRows = catalogProducts.map((cp) => {
    const product = cp.product ?? productMap.get(cp.productId);
    return {
      id: cp.productId,
      name: product?.name ?? cp.productId,
      sku: product?.sku ?? '—',
      price: cp.priceOverride ?? product?.unitPrice ?? 0,
      displayOrder: cp.displayOrder,
      priceOverride: cp.priceOverride,
      basePrice: product?.unitPrice ?? 0,
    };
  });

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/catalog/manage">Products</BreadcrumbItem>
        <BreadcrumbItem href="/catalog/manage/catalogs">Catalogs</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>{catalog.name}</BreadcrumbItem>
      </Breadcrumb>

      {/* Catalog Info Summary */}
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <Catalog size={24} className="text-interactive" />
            <h1 className="text-2xl font-semibold text-text-primary">{catalog.name}</h1>
            <StatusTag type={STATUS_TAG_COLOR[catalog.status]}>
              {catalog.status.charAt(0).toUpperCase() + catalog.status.slice(1)}
            </StatusTag>
          </div>
          {catalog.description && (
            <p className="text-sm text-text-secondary ml-9">{catalog.description}</p>
          )}
          <div className="flex gap-6 text-sm text-text-secondary ml-9 mt-1">
            <span>Payment: {paymentModelLabel(catalog.paymentModel)}</span>
            {catalog.buyingWindowOpensAt && catalog.buyingWindowClosesAt && (
              <span>
                Window: {formatDate(catalog.buyingWindowOpensAt)} – {formatDate(catalog.buyingWindowClosesAt)}
              </span>
            )}
            <span>Created: {formatDate(catalog.createdAt)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {isDraft && (
            <>
              <Button kind="tertiary" size="sm" renderIcon={Edit} onClick={openEditModal}>
                Edit
              </Button>
              <Button
                kind="primary"
                size="sm"
                renderIcon={SendFilled}
                onClick={() => {
                  if (catalogProducts.length === 0) {
                    showToast('error', 'Add at least one product before submitting');
                    return;
                  }
                  setSubmitConfirmOpen(true);
                }}
                disabled={submitCatalog.isPending}
              >
                Submit for Approval
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Products Section */}
      <div
        className="border rounded-lg p-4"
        style={{ borderColor: 'var(--cds-border-subtle-01)' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Products ({catalogProducts.length})
          </h2>
          {isDraft && (
            <Button kind="primary" size="sm" renderIcon={Add} onClick={() => setAddModalOpen(true)}>
              Add Product
            </Button>
          )}
        </div>

        {productsLoading ? (
          <div className="py-8 text-center text-text-secondary">Loading products...</div>
        ) : catalogProducts.length === 0 ? (
          <div className="py-8 text-center text-text-secondary">
            No products in this catalog yet.
            {isDraft && ' Click "Add Product" to get started.'}
          </div>
        ) : (
          <DataTable rows={productTableRows} headers={productTableHeaders} isSortable={false}>
            {({ rows: tableRowsProp, headers, getHeaderProps, getRowProps, getTableProps }) => (
              <TableContainer>
                <Table {...getTableProps()}>
                  <TableHead>
                    <TableRow>
                      {headers.map((header) => {
                        const { key, ...headerProps } = getHeaderProps({ header, isSortable: false });
                        return (
                          <TableHeader key={String(key)} {...headerProps}>
                            {header.header}
                          </TableHeader>
                        );
                      })}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {tableRowsProp.map((row) => {
                      const { key: rowKey, ...rowProps } = getRowProps({ row });
                      const rowData = productTableRows.find((r) => r.id === row.id);
                      if (!rowData) return null;
                      return (
                        <TableRow key={String(rowKey)} {...rowProps}>
                          {row.cells.map((cell) => (
                            <TableCell key={cell.id}>
                              {cell.info.header === 'price' ? (
                                <span>
                                  {currencyFmt.format(rowData.priceOverride ?? rowData.basePrice)}
                                  {rowData.priceOverride == null && (
                                    <span className="text-xs text-text-secondary ml-1">(base)</span>
                                  )}
                                  {rowData.priceOverride != null && (
                                    <span className="text-xs text-text-secondary ml-1">(override)</span>
                                  )}
                                </span>
                              ) : cell.info.header === 'actions' ? (
                                isDraft && (
                                  <Button
                                    kind="danger--ghost"
                                    size="sm"
                                    renderIcon={TrashCan}
                                    hasIconOnly
                                    iconDescription="Remove from catalog"
                                    onClick={() => setRemoveProductId(rowData.id)}
                                  />
                                )
                              ) : (
                                cell.value
                              )}
                            </TableCell>
                          ))}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DataTable>
        )}
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* Add Product Modal                                                    */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={addModalOpen}
        onRequestClose={() => {
          setAddModalOpen(false);
          setSelectedProduct(null);
          setAddDisplayOrder(0);
          setAddPriceOverride('');
        }}
        onRequestSubmit={handleAddProduct}
        modalHeading="Add Product to Catalog"
        primaryButtonText={addCatalogProduct.isPending ? 'Adding...' : 'Add Product'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={!selectedProduct || addCatalogProduct.isPending}
      >
        <div className="flex flex-col gap-4 mt-2">
          <ComboBox
            id="add-product-combobox"
            titleText="Product"
            placeholder="Search products..."
            items={availableProducts}
            itemToString={(item: Product | null) =>
              item ? `${item.name} (${item.sku})` : ''
            }
            selectedItem={selectedProduct}
            onChange={({ selectedItem }: { selectedItem: Product | null | undefined }) =>
              setSelectedProduct(selectedItem ?? null)
            }
          />
          {selectedProduct && (
            <p className="text-sm text-text-secondary">
              Base price: {currencyFmt.format(selectedProduct.unitPrice)}
            </p>
          )}
          <NumberInput
            id="add-display-order"
            label="Display Order"
            min={0}
            step={1}
            value={addDisplayOrder}
            onChange={(_e: React.SyntheticEvent, { value }: { value: number | string }) =>
              setAddDisplayOrder(value)
            }
            helperText="Lower numbers appear first"
          />
          <NumberInput
            id="add-price-override"
            label="Price Override (USD)"
            min={0}
            step={0.01}
            value={addPriceOverride}
            onChange={(_e: React.SyntheticEvent, { value }: { value: number | string }) =>
              setAddPriceOverride(value)
            }
            helperText="Leave empty to use the product's base price"
          />
        </div>
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Remove Product Confirmation                                          */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={removeProductId !== null}
        onRequestClose={() => setRemoveProductId(null)}
        onRequestSubmit={handleRemoveProduct}
        modalHeading="Remove Product"
        primaryButtonText={removeCatalogProduct.isPending ? 'Removing...' : 'Remove'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={removeCatalogProduct.isPending}
        danger
      >
        <p className="text-text-secondary">
          Are you sure you want to remove this product from the catalog?
        </p>
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Submit Confirmation                                                  */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={submitConfirmOpen}
        onRequestClose={() => setSubmitConfirmOpen(false)}
        onRequestSubmit={handleSubmit}
        modalHeading="Submit Catalog for Approval"
        primaryButtonText={submitCatalog.isPending ? 'Submitting...' : 'Submit'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={submitCatalog.isPending}
      >
        <p className="text-text-secondary">
          This catalog has {catalogProducts.length} product{catalogProducts.length !== 1 ? 's' : ''}.
          Once submitted, you will not be able to edit it or modify its products until it is
          returned to draft. Continue?
        </p>
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Edit Catalog Modal                                                   */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={editOpen}
        onRequestClose={() => setEditOpen(false)}
        onRequestSubmit={handleUpdate}
        modalHeading={`Edit: ${catalog.name}`}
        primaryButtonText={updateCatalog.isPending ? 'Saving...' : 'Save Changes'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={!editName.trim() || updateCatalog.isPending}
      >
        <div className="flex flex-col gap-4 mt-2">
          <TextInput
            id="edit-detail-catalog-name"
            labelText="Name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />
          <TextArea
            id="edit-detail-catalog-description"
            labelText="Description"
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
          />
        </div>
      </Modal>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <ToastNotification
            kind={toast.kind}
            title={toast.message}
            timeout={3000}
            onCloseButtonClick={() => setToast(null)}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </div>
  );
}
