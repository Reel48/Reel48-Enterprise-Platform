'use client';

import { useState } from 'react';
import {
  Button,
  ComboBox,
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
  TableToolbar,
  TableToolbarContent,
  TextArea,
  TextInput,
  ToastNotification,
} from '@carbon/react';
import { Add, Catalog as CatalogIcon } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';
import { usePlatformCompanies } from '@/hooks/usePlatformData';
import type { Catalog, CatalogStatus, PaymentModel, PlatformCatalogCreate } from '@/types/catalogs';

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

function statusColor(status: string): 'teal' | 'blue' | 'purple' | 'gray' | 'green' | 'red' {
  switch (status) {
    case 'active':
      return 'teal';
    case 'approved':
      return 'green';
    case 'submitted':
      return 'blue';
    case 'draft':
      return 'purple';
    case 'closed':
      return 'gray';
    default:
      return 'gray';
  }
}

const STATUS_OPTIONS = [
  { id: 'all', text: 'All Statuses' },
  { id: 'draft', text: 'Draft' },
  { id: 'submitted', text: 'Submitted' },
  { id: 'approved', text: 'Approved' },
  { id: 'active', text: 'Active' },
  { id: 'closed', text: 'Closed' },
];

const PAYMENT_MODEL_ITEMS = [
  { id: 'self_service', text: 'Self-Service' },
  { id: 'invoice_after_close', text: 'Invoice After Close' },
];

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function usePlatformCatalogs(page: number, perPage: number, status: string) {
  return useQuery({
    queryKey: ['platform-catalogs', page, perPage, status],
    queryFn: async () => {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (status && status !== 'all') params.status = status;
      const res = await api.get<Catalog[]>('/api/v1/platform/catalogs/', params);
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

function useCreatePlatformCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PlatformCatalogCreate) => {
      const res = await api.post<Catalog>('/api/v1/platform/catalogs/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-catalogs'] });
    },
  });
}

function useCatalogAction(action: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (catalogId: string) => {
      await api.post(`/api/v1/platform/catalogs/${catalogId}/${action}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-catalogs'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Table config
// ---------------------------------------------------------------------------

const tableHeaders = [
  { key: 'name', header: 'Catalog Name' },
  { key: 'companyName', header: 'Company' },
  { key: 'status', header: 'Status' },
  { key: 'paymentModel', header: 'Payment Model' },
  { key: 'createdAt', header: 'Created' },
  { key: 'actions', header: '' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PlatformCatalogsPage() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState('all');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  // Create modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [newCompanyId, setNewCompanyId] = useState('');
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newPaymentModel, setNewPaymentModel] = useState<PaymentModel | ''>('');
  const [newWindowOpens, setNewWindowOpens] = useState('');
  const [newWindowCloses, setNewWindowCloses] = useState('');

  const { data, isLoading, isError } = usePlatformCatalogs(page, perPage, statusFilter);
  const { data: companies } = usePlatformCompanies();
  const createCatalog = useCreatePlatformCatalog();
  const approveAction = useCatalogAction('approve');
  const rejectAction = useCatalogAction('reject');
  const activateAction = useCatalogAction('activate');
  const closeAction = useCatalogAction('close');

  const catalogs = data?.data ?? [];
  const total = data?.total ?? 0;

  const companyItems = (companies ?? []).map((c) => ({ id: c.id, text: c.name }));
  const companyNameMap = new Map(companyItems.map((c) => [c.id, c.text]));

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function showToast(kind: 'success' | 'error', message: string) {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  }

  function resetCreateForm() {
    setNewCompanyId('');
    setNewName('');
    setNewDescription('');
    setNewPaymentModel('');
    setNewWindowOpens('');
    setNewWindowCloses('');
  }

  // ---------------------------------------------------------------------------
  // Create handler
  // ---------------------------------------------------------------------------

  function handleCreate() {
    if (!newCompanyId || !newName.trim() || !newPaymentModel) return;

    const isInvoice = newPaymentModel === 'invoice_after_close';
    if (isInvoice && (!newWindowOpens || !newWindowCloses)) return;
    if (isInvoice && newWindowOpens >= newWindowCloses) return;

    const payload: PlatformCatalogCreate = {
      companyId: newCompanyId,
      name: newName.trim(),
      description: newDescription.trim() || undefined,
      paymentModel: newPaymentModel,
      buyingWindowOpensAt: isInvoice ? newWindowOpens : undefined,
      buyingWindowClosesAt: isInvoice ? newWindowCloses : undefined,
    };

    createCatalog.mutate(payload, {
      onSuccess: () => {
        showToast('success', 'Catalog created');
        setCreateOpen(false);
        resetCreateForm();
      },
      onError: () => {
        showToast('error', 'Failed to create catalog');
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Action handlers
  // ---------------------------------------------------------------------------

  const rows = catalogs.map((c) => ({
    id: c.id,
    name: c.name,
    companyName: companyNameMap.get(c.companyId) ?? c.companyId,
    status: c.status,
    paymentModel: c.paymentModel === 'self_service' ? 'Self-Service' : 'Invoice After Close',
    createdAt: c.createdAt,
  }));

  const handleAction = (action: ReturnType<typeof useCatalogAction>, id: string, label: string) => {
    action.mutate(id, {
      onSuccess: () => showToast('success', `Catalog ${label} successfully`),
      onError: () => showToast('error', `Failed to ${label.toLowerCase()} catalog`),
    });
  };

  const getAvailableActions = (status: CatalogStatus) => {
    switch (status) {
      case 'submitted':
        return ['approve', 'reject'];
      case 'approved':
        return ['activate'];
      case 'active':
        return ['close'];
      default:
        return [];
    }
  };

  const isInvoiceModel = newPaymentModel === 'invoice_after_close';

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">
          Catalog Management
        </h1>
        <Button
          kind="primary"
          size="sm"
          renderIcon={Add}
          onClick={() => setCreateOpen(true)}
        >
          Create Catalog
        </Button>
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load catalogs"
          hideCloseButton
        />
      )}

      <DataTable rows={rows} headers={tableHeaders} isSortable={false}>
        {({ rows: tRows, headers: tHeaders, getHeaderProps, getRowProps, getTableProps }) => (
          <TableContainer>
            <TableToolbar>
              <TableToolbarContent>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-medium" style={{ color: 'var(--cds-text-secondary)' }}>Filter:</span>
                  <Dropdown
                    id="catalog-status-filter"
                    titleText=""
                    label="Filter by status"
                    items={STATUS_OPTIONS}
                    itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
                    selectedItem={STATUS_OPTIONS.find((s) => s.id === statusFilter) ?? STATUS_OPTIONS[0]}
                    onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) => {
                      setStatusFilter(selectedItem?.id ?? 'all');
                      setPage(1);
                    }}
                    size="sm"
                  />
                </div>
              </TableToolbarContent>
            </TableToolbar>
            <Table {...getTableProps()}>
              <TableHead>
                <TableRow>
                  {tHeaders.map((header) => {
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
                      <div className="py-8 text-center text-text-secondary">
                        Loading catalogs...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : catalogs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center">
                        <CatalogIcon size={48} className="mx-auto mb-4 text-text-secondary" />
                        <p className="text-lg font-medium text-text-primary">
                          No catalogs found
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tRows.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const catalog = catalogs.find((c) => c.id === row.id);
                    const actions = catalog ? getAvailableActions(catalog.status) : [];
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => {
                          if (cell.info.header === 'status') {
                            return (
                              <TableCell key={cell.id}>
                                <StatusTag type={statusColor(cell.value as string)}>
                                  {cell.value as string}
                                </StatusTag>
                              </TableCell>
                            );
                          }
                          if (cell.info.header === 'createdAt') {
                            return (
                              <TableCell key={cell.id}>
                                {formatDate(cell.value as string)}
                              </TableCell>
                            );
                          }
                          if (cell.info.header === 'actions') {
                            return (
                              <TableCell key={cell.id}>
                                <div className="flex gap-2">
                                  {actions.includes('approve') && (
                                    <Button
                                      kind="primary"
                                      size="sm"
                                      onClick={() => handleAction(approveAction, row.id, 'approved')}
                                      disabled={approveAction.isPending}
                                    >
                                      Approve
                                    </Button>
                                  )}
                                  {actions.includes('reject') && (
                                    <Button
                                      kind="danger--ghost"
                                      size="sm"
                                      onClick={() => handleAction(rejectAction, row.id, 'rejected')}
                                      disabled={rejectAction.isPending}
                                    >
                                      Reject
                                    </Button>
                                  )}
                                  {actions.includes('activate') && (
                                    <Button
                                      kind="primary"
                                      size="sm"
                                      onClick={() => handleAction(activateAction, row.id, 'activated')}
                                      disabled={activateAction.isPending}
                                    >
                                      Activate
                                    </Button>
                                  )}
                                  {actions.includes('close') && (
                                    <Button
                                      kind="danger--ghost"
                                      size="sm"
                                      onClick={() => handleAction(closeAction, row.id, 'closed')}
                                      disabled={closeAction.isPending}
                                    >
                                      Close
                                    </Button>
                                  )}
                                </div>
                              </TableCell>
                            );
                          }
                          return <TableCell key={cell.id}>{cell.value as string}</TableCell>;
                        })}
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
          page={page}
          pageSize={perPage}
          pageSizes={[10, 20, 50]}
          totalItems={total}
          onChange={({ page: p, pageSize }: { page: number; pageSize: number }) => {
            setPage(p);
            setPerPage(pageSize);
          }}
        />
      )}

      {/* Create Catalog Modal */}
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
          !newCompanyId ||
          !newName.trim() ||
          !newPaymentModel ||
          (isInvoiceModel && (!newWindowOpens || !newWindowCloses)) ||
          (isInvoiceModel && newWindowOpens >= newWindowCloses) ||
          createCatalog.isPending
        }
      >
        <div className="flex flex-col gap-4 mt-2">
          <ComboBox
            id="create-catalog-company"
            titleText="Company"
            placeholder="Search companies..."
            items={companyItems}
            itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
            selectedItem={companyItems.find((c) => c.id === newCompanyId) ?? null}
            onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) =>
              setNewCompanyId(selectedItem?.id ?? '')
            }
          />
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
            itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
            selectedItem={PAYMENT_MODEL_ITEMS.find((p) => p.id === newPaymentModel) ?? null}
            onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) => {
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
