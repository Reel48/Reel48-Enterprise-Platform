'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Button,
  DataTable,
  DatePicker,
  DatePickerInput,
  Dropdown,
  InlineNotification,
  Modal,
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
import { Catalog, Add, Edit, TrashCan, SendFilled, Settings } from '@carbon/react/icons';

import { useAuth, useHasRole } from '@/lib/auth/hooks';
import { StatusTag } from '@/components/ui/StatusTag';
import type { CatalogStatus, PaymentModel } from '@/types/catalogs';
import {
  useCatalogs,
  useCreateCatalog,
  useUpdateCatalog,
  useDeleteCatalog,
  useSubmitCatalog,
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

function toISODate(date: Date): string {
  return date.toISOString().split('T')[0];
}

const STATUS_TAG_COLOR: Record<CatalogStatus, 'gray' | 'blue' | 'teal' | 'green' | 'red' | 'purple'> = {
  draft: 'gray',
  submitted: 'blue',
  approved: 'teal',
  active: 'green',
  closed: 'purple',
  archived: 'red',
};

const STATUS_ITEMS = [
  { id: 'all', text: 'All Statuses' },
  { id: 'draft', text: 'Draft' },
  { id: 'submitted', text: 'Submitted' },
  { id: 'approved', text: 'Approved' },
  { id: 'active', text: 'Active' },
  { id: 'closed', text: 'Closed' },
  { id: 'archived', text: 'Archived' },
];

const PAYMENT_MODEL_ITEMS = [
  { id: 'self_service', text: 'Self-Service' },
  { id: 'invoice_after_close', text: 'Invoice After Close' },
];

function paymentModelLabel(model: PaymentModel): string {
  return model === 'self_service' ? 'Self-Service' : 'Invoice After Close';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CatalogManagementPage() {
  const router = useRouter();
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

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState('all');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newPaymentModel, setNewPaymentModel] = useState<PaymentModel | ''>('');
  const [newWindowOpens, setNewWindowOpens] = useState('');
  const [newWindowCloses, setNewWindowCloses] = useState('');

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editId, setEditId] = useState('');
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editWindowOpens, setEditWindowOpens] = useState('');
  const [editWindowCloses, setEditWindowCloses] = useState('');

  // Delete modal
  const [deleteCatalogId, setDeleteCatalogId] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Data hooks
  // ---------------------------------------------------------------------------

  const { data, isLoading, isError } = useCatalogs(page, perPage, statusFilter);
  const createCatalog = useCreateCatalog();
  const updateCatalog = useUpdateCatalog();
  const deleteCatalog = useDeleteCatalog();
  const submitCatalog = useSubmitCatalog();

  const catalogs = data?.data ?? [];
  const total = Number(data?.meta?.total ?? 0);

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

  function resetCreateForm() {
    setNewName('');
    setNewDescription('');
    setNewPaymentModel('');
    setNewWindowOpens('');
    setNewWindowCloses('');
  }

  function handleCreate() {
    if (!newName.trim() || !newPaymentModel) return;

    const isInvoice = newPaymentModel === 'invoice_after_close';
    if (isInvoice && (!newWindowOpens || !newWindowCloses)) return;
    if (isInvoice && newWindowOpens >= newWindowCloses) return;

    createCatalog.mutate(
      {
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        paymentModel: newPaymentModel,
        buyingWindowOpensAt: isInvoice ? newWindowOpens : undefined,
        buyingWindowClosesAt: isInvoice ? newWindowCloses : undefined,
      },
      {
        onSuccess: () => {
          showToast('success', 'Catalog created');
          setCreateOpen(false);
          resetCreateForm();
        },
        onError: () => {
          showToast('error', 'Failed to create catalog');
        },
      },
    );
  }

  function openEditModal(catalog: (typeof catalogs)[number]) {
    setEditId(catalog.id);
    setEditName(catalog.name);
    setEditDescription(catalog.description ?? '');
    setEditWindowOpens(catalog.buyingWindowOpensAt ? catalog.buyingWindowOpensAt.split('T')[0] : '');
    setEditWindowCloses(catalog.buyingWindowClosesAt ? catalog.buyingWindowClosesAt.split('T')[0] : '');
    setEditOpen(true);
  }

  function handleUpdate() {
    if (!editName.trim()) return;

    updateCatalog.mutate(
      {
        id: editId,
        data: {
          name: editName.trim(),
          description: editDescription.trim() || undefined,
          buyingWindowOpensAt: editWindowOpens || undefined,
          buyingWindowClosesAt: editWindowCloses || undefined,
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

  function handleDelete() {
    if (!deleteCatalogId) return;
    deleteCatalog.mutate(deleteCatalogId, {
      onSuccess: () => {
        showToast('success', 'Catalog deleted');
        setDeleteCatalogId(null);
      },
      onError: () => {
        showToast('error', 'Failed to delete catalog');
        setDeleteCatalogId(null);
      },
    });
  }

  function handleSubmit(id: string) {
    submitCatalog.mutate(id, {
      onSuccess: () => showToast('success', 'Catalog submitted for approval'),
      onError: (err) => showToast('error', err.message || 'Failed to submit catalog'),
    });
  }

  // ---------------------------------------------------------------------------
  // Guard
  // ---------------------------------------------------------------------------

  if (!user || !isAdmin) return null;

  // ---------------------------------------------------------------------------
  // DataTable setup
  // ---------------------------------------------------------------------------

  const tableHeaders = [
    { key: 'name', header: 'Name' },
    { key: 'paymentModel', header: 'Payment Model' },
    { key: 'status', header: 'Status' },
    { key: 'buyingWindow', header: 'Buying Window' },
    { key: 'createdAt', header: 'Created' },
    { key: 'actions', header: '' },
  ];

  const tableRows = catalogs.map((c) => ({
    id: c.id,
    name: c.name,
    paymentModel: c.paymentModel,
    status: c.status,
    buyingWindow: c.buyingWindowOpensAt,
    createdAt: c.createdAt,
  }));

  const isDraft = (id: string) => {
    const cat = catalogs.find((c) => c.id === id);
    return cat?.status === 'draft';
  };

  const isInvoiceModel = newPaymentModel === 'invoice_after_close';
  const editCatalog = catalogs.find((c) => c.id === editId);
  const editIsInvoiceModel = editCatalog?.paymentModel === 'invoice_after_close';

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Catalog size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">Catalog Management</h1>
        </div>
        <Button kind="primary" size="sm" renderIcon={Add} onClick={() => setCreateOpen(true)}>
          Create Catalog
        </Button>
      </div>

      {/* Status Filter */}
      <div className="w-64">
        <Dropdown
          id="catalog-status-filter"
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
          title="Failed to load catalogs"
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
                      <div className="py-8 text-center text-text-secondary">Loading catalogs...</div>
                    </TableCell>
                  </TableRow>
                ) : tableRowsProp.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">No catalogs found.</div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRowsProp.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const original = catalogs.find((c) => c.id === row.id);
                    if (!original) return null;
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'paymentModel' ? (
                              paymentModelLabel(original.paymentModel)
                            ) : cell.info.header === 'status' ? (
                              <StatusTag type={STATUS_TAG_COLOR[original.status]}>
                                {original.status.charAt(0).toUpperCase() + original.status.slice(1)}
                              </StatusTag>
                            ) : cell.info.header === 'buyingWindow' ? (
                              original.buyingWindowOpensAt && original.buyingWindowClosesAt
                                ? `${formatDate(original.buyingWindowOpensAt)} – ${formatDate(original.buyingWindowClosesAt)}`
                                : '—'
                            ) : cell.info.header === 'createdAt' ? (
                              formatDate(original.createdAt)
                            ) : cell.info.header === 'actions' ? (
                              <div className="flex gap-2">
                                <Button
                                  kind="ghost"
                                  size="sm"
                                  renderIcon={Settings}
                                  hasIconOnly
                                  iconDescription="Manage"
                                  onClick={() => router.push(`/catalog/manage/catalogs/${original.id}`)}
                                />
                                {isDraft(original.id) && (
                                  <>
                                    <Button
                                      kind="ghost"
                                      size="sm"
                                      renderIcon={Edit}
                                      hasIconOnly
                                      iconDescription="Edit"
                                      onClick={() => openEditModal(original)}
                                    />
                                    <Button
                                      kind="ghost"
                                      size="sm"
                                      renderIcon={SendFilled}
                                      hasIconOnly
                                      iconDescription="Submit for approval"
                                      onClick={() => handleSubmit(original.id)}
                                      disabled={submitCatalog.isPending}
                                    />
                                    <Button
                                      kind="danger--ghost"
                                      size="sm"
                                      renderIcon={TrashCan}
                                      hasIconOnly
                                      iconDescription="Delete"
                                      onClick={() => setDeleteCatalogId(original.id)}
                                    />
                                  </>
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
      {/* Create Catalog Modal                                                 */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={createOpen}
        onRequestClose={() => {
          setCreateOpen(false);
          resetCreateForm();
        }}
        onRequestSubmit={handleCreate}
        modalHeading="Create Catalog"
        primaryButtonText={createCatalog.isPending ? 'Creating...' : 'Create'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={
          !newName.trim() ||
          !newPaymentModel ||
          (isInvoiceModel && (!newWindowOpens || !newWindowCloses)) ||
          (isInvoiceModel && newWindowOpens >= newWindowCloses) ||
          createCatalog.isPending
        }
      >
        <div className="flex flex-col gap-4 mt-2">
          <TextInput
            id="create-catalog-name"
            labelText="Name"
            placeholder="e.g., Spring 2026 Collection"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
          />
          <TextArea
            id="create-catalog-description"
            labelText="Description"
            placeholder="Optional catalog description"
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
          />
          <Dropdown
            id="create-catalog-payment-model"
            titleText="Payment Model"
            label="Select payment model"
            items={PAYMENT_MODEL_ITEMS}
            itemToString={(item) => item?.text ?? ''}
            selectedItem={PAYMENT_MODEL_ITEMS.find((p) => p.id === newPaymentModel) ?? null}
            onChange={({ selectedItem }) => {
              const model = (selectedItem?.id ?? '') as PaymentModel | '';
              setNewPaymentModel(model);
              if (model !== 'invoice_after_close') {
                setNewWindowOpens('');
                setNewWindowCloses('');
              }
            }}
          />
          {isInvoiceModel && (
            <>
              <DatePicker
                datePickerType="single"
                onChange={(dates: Date[]) => {
                  if (dates[0]) setNewWindowOpens(toISODate(dates[0]));
                }}
              >
                <DatePickerInput
                  id="create-window-opens"
                  labelText="Buying Window Opens"
                  placeholder="mm/dd/yyyy"
                />
              </DatePicker>
              <DatePicker
                datePickerType="single"
                onChange={(dates: Date[]) => {
                  if (dates[0]) setNewWindowCloses(toISODate(dates[0]));
                }}
              >
                <DatePickerInput
                  id="create-window-closes"
                  labelText="Buying Window Closes"
                  placeholder="mm/dd/yyyy"
                />
              </DatePicker>
              {newWindowOpens && newWindowCloses && newWindowOpens >= newWindowCloses && (
                <InlineNotification
                  kind="error"
                  title="Invalid dates"
                  subtitle="Opening date must be before closing date."
                  hideCloseButton
                  lowContrast
                />
              )}
            </>
          )}
        </div>
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Edit Catalog Modal                                                   */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={editOpen}
        onRequestClose={() => setEditOpen(false)}
        onRequestSubmit={handleUpdate}
        modalHeading={editCatalog ? `Edit: ${editCatalog.name}` : 'Edit Catalog'}
        primaryButtonText={updateCatalog.isPending ? 'Saving...' : 'Save Changes'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={!editName.trim() || updateCatalog.isPending}
      >
        <div className="flex flex-col gap-4 mt-2">
          <TextInput
            id="edit-catalog-name"
            labelText="Name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />
          <TextArea
            id="edit-catalog-description"
            labelText="Description"
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
          />
          {editIsInvoiceModel && (
            <>
              <DatePicker
                datePickerType="single"
                value={editWindowOpens}
                onChange={(dates: Date[]) => {
                  if (dates[0]) setEditWindowOpens(toISODate(dates[0]));
                }}
              >
                <DatePickerInput
                  id="edit-window-opens"
                  labelText="Buying Window Opens"
                  placeholder="mm/dd/yyyy"
                />
              </DatePicker>
              <DatePicker
                datePickerType="single"
                value={editWindowCloses}
                onChange={(dates: Date[]) => {
                  if (dates[0]) setEditWindowCloses(toISODate(dates[0]));
                }}
              >
                <DatePickerInput
                  id="edit-window-closes"
                  labelText="Buying Window Closes"
                  placeholder="mm/dd/yyyy"
                />
              </DatePicker>
            </>
          )}
        </div>
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Delete Confirmation Modal                                            */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={deleteCatalogId !== null}
        onRequestClose={() => setDeleteCatalogId(null)}
        onRequestSubmit={handleDelete}
        modalHeading="Delete Catalog"
        primaryButtonText={deleteCatalog.isPending ? 'Deleting...' : 'Delete'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={deleteCatalog.isPending}
        danger
      >
        <p className="text-text-secondary">
          Are you sure you want to delete this catalog? This action cannot be undone.
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
