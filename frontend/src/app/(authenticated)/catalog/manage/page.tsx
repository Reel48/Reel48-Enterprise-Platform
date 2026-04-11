'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Button,
  DataTable,
  Dropdown,
  InlineNotification,
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
import { Catalog, Add, Edit, TrashCan, SendFilled, Upload } from '@carbon/react/icons';

import { useAuth, useHasRole } from '@/lib/auth/hooks';
import { useFileUpload } from '@/hooks/useStorage';
import { StatusTag } from '@/components/ui/StatusTag';
import { S3Image } from '@/components/ui/S3Image';
import type { Product, ProductStatus } from '@/types/products';
import {
  useProducts,
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  useSubmitProduct,
  useAddProductImage,
  useRemoveProductImage,
} from './_hooks';

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

const STATUS_TAG_COLOR: Record<ProductStatus, 'gray' | 'blue' | 'teal' | 'green' | 'red'> = {
  draft: 'gray',
  submitted: 'blue',
  approved: 'teal',
  active: 'green',
  archived: 'red',
};

const STATUS_ITEMS = [
  { id: 'all', text: 'All Statuses' },
  { id: 'draft', text: 'Draft' },
  { id: 'submitted', text: 'Submitted' },
  { id: 'approved', text: 'Approved' },
  { id: 'active', text: 'Active' },
  { id: 'archived', text: 'Archived' },
];

function parseCommaSeparated(value: string): string[] {
  return value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ProductManagementPage() {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = useHasRole(['sub_brand_admin', 'corporate_admin', 'reel48_admin']);

  // Redirect non-admins
  useEffect(() => {
    if (user && !isAdmin) {
      router.replace('/catalog');
    }
  }, [user, isAdmin, router]);

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState('all');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSku, setNewSku] = useState('');
  const [newPrice, setNewPrice] = useState<number | string>('');
  const [newDescription, setNewDescription] = useState('');
  const [newSizes, setNewSizes] = useState('');
  const [newDecorationOptions, setNewDecorationOptions] = useState('');

  // Edit modal
  const [editProduct, setEditProduct] = useState<Product | null>(null);
  const [editName, setEditName] = useState('');
  const [editSku, setEditSku] = useState('');
  const [editPrice, setEditPrice] = useState<number | string>('');
  const [editDescription, setEditDescription] = useState('');
  const [editSizes, setEditSizes] = useState('');
  const [editDecorationOptions, setEditDecorationOptions] = useState('');

  // Delete modal
  const [deleteProductId, setDeleteProductId] = useState<string | null>(null);

  // File input ref for image upload
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---------------------------------------------------------------------------
  // Data hooks
  // ---------------------------------------------------------------------------

  const { data, isLoading, isError } = useProducts(page, perPage, statusFilter);
  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct();
  const deleteProduct = useDeleteProduct();
  const submitProduct = useSubmitProduct();
  const addProductImage = useAddProductImage();
  const removeProductImage = useRemoveProductImage();
  const fileUpload = useFileUpload();

  const products = data?.data ?? [];
  const total = Number(data?.meta?.total ?? 0);

  // ---------------------------------------------------------------------------
  // Populate edit form when editProduct changes
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (editProduct) {
      setEditName(editProduct.name);
      setEditSku(editProduct.sku);
      setEditPrice(editProduct.unitPrice);
      setEditDescription(editProduct.description ?? '');
      setEditSizes(editProduct.sizes.join(', '));
      setEditDecorationOptions(editProduct.decorationOptions.join(', '));
    }
  }, [editProduct]);

  // ---------------------------------------------------------------------------
  // Toast helper
  // ---------------------------------------------------------------------------

  function showToast(kind: 'success' | 'error', message: string) {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  function resetCreateForm() {
    setNewName('');
    setNewSku('');
    setNewPrice('');
    setNewDescription('');
    setNewSizes('');
    setNewDecorationOptions('');
  }

  function handleCreate() {
    const price = typeof newPrice === 'string' ? parseFloat(newPrice) : newPrice;
    if (!newName.trim() || !newSku.trim() || isNaN(price) || price < 0) return;

    createProduct.mutate(
      {
        name: newName.trim(),
        sku: newSku.trim(),
        unitPrice: price,
        description: newDescription.trim() || undefined,
        sizes: newSizes.trim() ? parseCommaSeparated(newSizes) : undefined,
        decorationOptions: newDecorationOptions.trim()
          ? parseCommaSeparated(newDecorationOptions)
          : undefined,
      },
      {
        onSuccess: () => {
          showToast('success', 'Product created');
          setCreateOpen(false);
          resetCreateForm();
        },
        onError: () => {
          showToast('error', 'Failed to create product');
        },
      },
    );
  }

  function handleUpdate() {
    if (!editProduct) return;
    const price = typeof editPrice === 'string' ? parseFloat(editPrice) : editPrice;
    if (!editName.trim() || !editSku.trim() || isNaN(price) || price < 0) return;

    updateProduct.mutate(
      {
        id: editProduct.id,
        data: {
          name: editName.trim(),
          sku: editSku.trim(),
          unitPrice: price,
          description: editDescription.trim() || undefined,
          sizes: parseCommaSeparated(editSizes),
          decorationOptions: parseCommaSeparated(editDecorationOptions),
        },
      },
      {
        onSuccess: () => {
          showToast('success', 'Product updated');
          setEditProduct(null);
        },
        onError: () => {
          showToast('error', 'Failed to update product');
        },
      },
    );
  }

  function handleDelete() {
    if (!deleteProductId) return;
    deleteProduct.mutate(deleteProductId, {
      onSuccess: () => {
        showToast('success', 'Product deleted');
        setDeleteProductId(null);
      },
      onError: () => {
        showToast('error', 'Failed to delete product');
        setDeleteProductId(null);
      },
    });
  }

  function handleSubmit(id: string) {
    submitProduct.mutate(id, {
      onSuccess: () => showToast('success', 'Product submitted for approval'),
      onError: () => showToast('error', 'Failed to submit product'),
    });
  }

  function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !editProduct) return;

    fileUpload.mutate(
      { file, category: 'products' },
      {
        onSuccess: (s3Key) => {
          addProductImage.mutate(
            { productId: editProduct.id, s3Key },
            {
              onSuccess: (updatedProduct) => {
                setEditProduct(updatedProduct);
                showToast('success', 'Image uploaded');
              },
              onError: () => showToast('error', 'Failed to add image'),
            },
          );
        },
        onError: (err) => {
          showToast('error', err.message || 'Failed to upload image');
        },
      },
    );

    // Reset the file input so the same file can be re-selected
    e.target.value = '';
  }

  function handleRemoveImage(index: number) {
    if (!editProduct) return;
    removeProductImage.mutate(
      { productId: editProduct.id, index },
      {
        onSuccess: (updatedProduct) => {
          setEditProduct(updatedProduct);
          showToast('success', 'Image removed');
        },
        onError: () => showToast('error', 'Failed to remove image'),
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Don't render until we know the user is an admin
  // ---------------------------------------------------------------------------

  if (!user || !isAdmin) return null;

  // ---------------------------------------------------------------------------
  // DataTable setup
  // ---------------------------------------------------------------------------

  const tableHeaders = [
    { key: 'name', header: 'Name' },
    { key: 'sku', header: 'SKU' },
    { key: 'unitPrice', header: 'Price' },
    { key: 'status', header: 'Status' },
    { key: 'createdAt', header: 'Created' },
    { key: 'actions', header: '' },
  ];

  const tableRows = products.map((p) => ({
    id: p.id,
    name: p.name,
    sku: p.sku,
    unitPrice: p.unitPrice,
    status: p.status,
    createdAt: p.createdAt,
  }));

  const isDraft = (product: Product) => product.status === 'draft';
  const isImageBusy = fileUpload.isPending || addProductImage.isPending || removeProductImage.isPending;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Catalog size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">Product Management</h1>
        </div>
        <Button kind="primary" size="sm" renderIcon={Add} onClick={() => setCreateOpen(true)}>
          Create Product
        </Button>
      </div>

      {/* Status Filter */}
      <div className="w-64">
        <Dropdown
          id="status-filter"
          titleText=""
          label="Filter by status"
          items={STATUS_ITEMS}
          itemToString={(item) => item?.text ?? ''}
          selectedItem={STATUS_ITEMS.find((s) => s.id === statusFilter) ?? STATUS_ITEMS[0]}
          onChange={({ selectedItem }) => {
            setStatusFilter(selectedItem?.id ?? 'all');
            setPage(1);
          }}
        />
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load products"
          subtitle="Please try refreshing the page."
          hideCloseButton
        />
      )}

      {/* DataTable */}
      <DataTable rows={tableRows} headers={tableHeaders} isSortable={false}>
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
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">Loading products...</div>
                    </TableCell>
                  </TableRow>
                ) : tableRowsProp.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">No products found.</div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRowsProp.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const original = products.find((p) => p.id === row.id);
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'unitPrice' && original ? (
                              currencyFmt.format(original.unitPrice)
                            ) : cell.info.header === 'status' && original ? (
                              <StatusTag type={STATUS_TAG_COLOR[original.status as ProductStatus]}>
                                {original.status.charAt(0).toUpperCase() + original.status.slice(1)}
                              </StatusTag>
                            ) : cell.info.header === 'createdAt' && original ? (
                              formatDate(original.createdAt)
                            ) : cell.info.header === 'actions' && original ? (
                              <div className="flex gap-2">
                                {isDraft(original) && (
                                  <>
                                    <Button
                                      kind="ghost"
                                      size="sm"
                                      renderIcon={Edit}
                                      hasIconOnly
                                      iconDescription="Edit"
                                      onClick={() => setEditProduct(original)}
                                    />
                                    <Button
                                      kind="ghost"
                                      size="sm"
                                      renderIcon={SendFilled}
                                      hasIconOnly
                                      iconDescription="Submit for approval"
                                      onClick={() => handleSubmit(original.id)}
                                      disabled={submitProduct.isPending}
                                    />
                                    <Button
                                      kind="danger--ghost"
                                      size="sm"
                                      renderIcon={TrashCan}
                                      hasIconOnly
                                      iconDescription="Delete"
                                      onClick={() => setDeleteProductId(original.id)}
                                    />
                                  </>
                                )}
                                {!isDraft(original) && (
                                  <Button
                                    kind="ghost"
                                    size="sm"
                                    renderIcon={Edit}
                                    hasIconOnly
                                    iconDescription="View details"
                                    onClick={() => setEditProduct(original)}
                                  />
                                )}
                              </div>
                            ) : (
                              cell.value
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DataTable>

      {total > perPage && (
        <Pagination
          totalItems={total}
          pageSize={perPage}
          pageSizes={[10, 20, 50]}
          page={page}
          onChange={({ page: p, pageSize }) => {
            setPage(p);
            setPerPage(pageSize);
          }}
        />
      )}

      {/* ------------------------------------------------------------------- */}
      {/* Create Product Modal                                                 */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={createOpen}
        onRequestClose={() => {
          setCreateOpen(false);
          resetCreateForm();
        }}
        onRequestSubmit={handleCreate}
        modalHeading="Create Product"
        primaryButtonText={createProduct.isPending ? 'Creating...' : 'Create'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={
          !newName.trim() ||
          !newSku.trim() ||
          newPrice === '' ||
          createProduct.isPending
        }
      >
        <div className="flex flex-col gap-4 mt-2">
          <TextInput
            id="create-name"
            labelText="Name"
            placeholder="e.g., Classic Polo Shirt"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
          />
          <TextInput
            id="create-sku"
            labelText="SKU"
            placeholder="e.g., POLO-BLK-001"
            value={newSku}
            onChange={(e) => setNewSku(e.target.value)}
            required
          />
          <NumberInput
            id="create-price"
            label="Unit Price (USD)"
            min={0}
            step={0.01}
            value={newPrice}
            onChange={(_e: React.SyntheticEvent, { value }: { value: number | string }) =>
              setNewPrice(value)
            }
            required
          />
          <TextArea
            id="create-description"
            labelText="Description"
            placeholder="Optional product description"
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
          />
          <TextInput
            id="create-sizes"
            labelText="Sizes"
            placeholder="e.g., S, M, L, XL"
            value={newSizes}
            onChange={(e) => setNewSizes(e.target.value)}
            helperText="Comma-separated list"
          />
          <TextInput
            id="create-decoration"
            labelText="Decoration Options"
            placeholder="e.g., Embroidered, Screen Print"
            value={newDecorationOptions}
            onChange={(e) => setNewDecorationOptions(e.target.value)}
            helperText="Comma-separated list"
          />
        </div>
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Edit Product Modal                                                   */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={editProduct !== null}
        onRequestClose={() => setEditProduct(null)}
        onRequestSubmit={handleUpdate}
        modalHeading={editProduct ? `Edit: ${editProduct.name}` : 'Edit Product'}
        primaryButtonText={updateProduct.isPending ? 'Saving...' : 'Save Changes'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={
          !editProduct ||
          !isDraft(editProduct) ||
          !editName.trim() ||
          !editSku.trim() ||
          editPrice === '' ||
          updateProduct.isPending
        }
        size="lg"
      >
        {editProduct && (
          <div className="flex flex-col gap-4 mt-2">
            {!isDraft(editProduct) && (
              <InlineNotification
                kind="info"
                title="Read-only"
                subtitle="Only draft products can be edited."
                hideCloseButton
                lowContrast
              />
            )}
            <TextInput
              id="edit-name"
              labelText="Name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              disabled={!isDraft(editProduct)}
              required
            />
            <TextInput
              id="edit-sku"
              labelText="SKU"
              value={editSku}
              onChange={(e) => setEditSku(e.target.value)}
              disabled={!isDraft(editProduct)}
              required
            />
            <NumberInput
              id="edit-price"
              label="Unit Price (USD)"
              min={0}
              step={0.01}
              value={editPrice}
              onChange={(_e: React.SyntheticEvent, { value }: { value: number | string }) =>
                setEditPrice(value)
              }
              disabled={!isDraft(editProduct)}
              required
            />
            <TextArea
              id="edit-description"
              labelText="Description"
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              disabled={!isDraft(editProduct)}
            />
            <TextInput
              id="edit-sizes"
              labelText="Sizes"
              value={editSizes}
              onChange={(e) => setEditSizes(e.target.value)}
              disabled={!isDraft(editProduct)}
              helperText="Comma-separated list"
            />
            <TextInput
              id="edit-decoration"
              labelText="Decoration Options"
              value={editDecorationOptions}
              onChange={(e) => setEditDecorationOptions(e.target.value)}
              disabled={!isDraft(editProduct)}
              helperText="Comma-separated list"
            />

            {/* Image Management */}
            <div className="mt-4 pt-4 border-t border-solid" style={{ borderColor: 'var(--cds-border-subtle-01)' }}>
              <h4 className="text-sm font-semibold text-text-primary mb-3">Product Images</h4>

              {editProduct.imageUrls.length > 0 ? (
                <div className="flex flex-wrap gap-3 mb-4">
                  {editProduct.imageUrls.map((url, index) => (
                    <div key={`${url}-${index}`} className="relative">
                      <S3Image s3Key={url} alt={`Product image ${index + 1}`} width={80} height={80} />
                      {isDraft(editProduct) && (
                        <button
                          type="button"
                          className="absolute -top-2 -right-2 w-5 h-5 rounded-full flex items-center justify-center text-xs text-white"
                          style={{ backgroundColor: 'var(--cds-support-error)' }}
                          onClick={() => handleRemoveImage(index)}
                          disabled={isImageBusy}
                          title="Remove image"
                        >
                          &times;
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-secondary mb-4">No images uploaded.</p>
              )}

              {isDraft(editProduct) && (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="hidden"
                    onChange={handleImageUpload}
                  />
                  <Button
                    kind="tertiary"
                    size="sm"
                    renderIcon={Upload}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isImageBusy}
                  >
                    {fileUpload.isPending ? 'Uploading...' : 'Upload Image'}
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Delete Confirmation Modal                                            */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={deleteProductId !== null}
        onRequestClose={() => setDeleteProductId(null)}
        onRequestSubmit={handleDelete}
        modalHeading="Delete Product"
        primaryButtonText={deleteProduct.isPending ? 'Deleting...' : 'Delete'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={deleteProduct.isPending}
        danger
      >
        <p className="text-text-secondary">
          Are you sure you want to delete this product? This action cannot be undone.
        </p>
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
