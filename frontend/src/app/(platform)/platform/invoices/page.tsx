'use client';

import { useState } from 'react';
import {
  Button,
  DataTable,
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
  Tag,
  TextInput,
  ToastNotification,
} from '@carbon/react';
import { Add, Receipt } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';
import type { Invoice, InvoiceStatus } from '@/types/invoices';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function statusColor(status: string): 'teal' | 'blue' | 'purple' | 'gray' | 'green' | 'red' {
  switch (status) {
    case 'paid':
      return 'green';
    case 'sent':
      return 'blue';
    case 'finalized':
      return 'teal';
    case 'draft':
      return 'purple';
    case 'payment_failed':
      return 'red';
    case 'voided':
      return 'red';
    default:
      return 'gray';
  }
}

function billingFlowLabel(flow: string): string {
  switch (flow) {
    case 'assigned':
      return 'Assigned';
    case 'self_service':
      return 'Self-Service';
    case 'post_window':
      return 'Post-Window';
    default:
      return flow;
  }
}

const STATUS_OPTIONS = [
  { id: 'all', text: 'All Statuses' },
  { id: 'draft', text: 'Draft' },
  { id: 'finalized', text: 'Finalized' },
  { id: 'sent', text: 'Sent' },
  { id: 'paid', text: 'Paid' },
  { id: 'payment_failed', text: 'Payment Failed' },
  { id: 'voided', text: 'Voided' },
];

const FLOW_OPTIONS = [
  { id: 'all', text: 'All Flows' },
  { id: 'assigned', text: 'Assigned' },
  { id: 'self_service', text: 'Self-Service' },
  { id: 'post_window', text: 'Post-Window' },
];

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function usePlatformInvoices(
  page: number,
  perPage: number,
  status: string,
  billingFlow: string,
) {
  return useQuery({
    queryKey: ['platform-invoices', page, perPage, status, billingFlow],
    queryFn: async () => {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (status && status !== 'all') params.status = status;
      if (billingFlow && billingFlow !== 'all') params.billing_flow = billingFlow;
      const res = await api.get<Invoice[]>('/api/v1/platform/invoices/', params);
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

function useCreateInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { companyId: string; billingFlow: string }) => {
      const res = await api.post<Invoice>('/api/v1/platform/invoices/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-invoices'] });
    },
  });
}

function useInvoiceAction(action: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invoiceId: string) => {
      await api.post(`/api/v1/platform/invoices/${invoiceId}/${action}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-invoices'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Table config
// ---------------------------------------------------------------------------

const tableHeaders = [
  { key: 'invoiceNumber', header: 'Invoice #' },
  { key: 'companyId', header: 'Company' },
  { key: 'billingFlow', header: 'Flow' },
  { key: 'status', header: 'Status' },
  { key: 'totalAmount', header: 'Amount' },
  { key: 'createdAt', header: 'Created' },
  { key: 'actions', header: '' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PlatformInvoicesPage() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState('all');
  const [flowFilter, setFlowFilter] = useState('all');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  // Create invoice modal state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newCompanyId, setNewCompanyId] = useState('');
  const [newBillingFlow, setNewBillingFlow] = useState('assigned');

  const { data, isLoading, isError } = usePlatformInvoices(page, perPage, statusFilter, flowFilter);
  const createInvoice = useCreateInvoice();
  const finalizeAction = useInvoiceAction('finalize');
  const sendAction = useInvoiceAction('send');
  const voidAction = useInvoiceAction('void');

  const invoices = data?.data ?? [];
  const total = data?.total ?? 0;

  const rows = invoices.map((inv) => ({
    id: inv.id,
    invoiceNumber: inv.invoiceNumber ?? 'Draft',
    companyId: inv.companyId ?? '—',
    billingFlow: inv.billingFlow,
    status: inv.status,
    totalAmount: inv.totalAmount,
    createdAt: inv.createdAt,
  }));

  const handleCreate = () => {
    if (!newCompanyId.trim()) return;
    createInvoice.mutate(
      { companyId: newCompanyId, billingFlow: newBillingFlow },
      {
        onSuccess: () => {
          setCreateModalOpen(false);
          setNewCompanyId('');
          setNewBillingFlow('assigned');
          setToast({ kind: 'success', message: 'Draft invoice created' });
          setTimeout(() => setToast(null), 3000);
        },
        onError: () => {
          setToast({ kind: 'error', message: 'Failed to create invoice' });
          setTimeout(() => setToast(null), 3000);
        },
      },
    );
  };

  const handleInvoiceAction = (
    action: ReturnType<typeof useInvoiceAction>,
    id: string,
    label: string,
  ) => {
    action.mutate(id, {
      onSuccess: () => {
        setToast({ kind: 'success', message: `Invoice ${label} successfully` });
        setTimeout(() => setToast(null), 3000);
      },
      onError: () => {
        setToast({ kind: 'error', message: `Failed to ${label.toLowerCase()} invoice` });
        setTimeout(() => setToast(null), 3000);
      },
    });
  };

  const getAvailableActions = (status: InvoiceStatus): string[] => {
    switch (status) {
      case 'draft':
        return ['finalize', 'void'];
      case 'finalized':
        return ['send', 'void'];
      case 'sent':
        return ['void'];
      default:
        return [];
    }
  };

  const CREATE_FLOW_OPTIONS = [
    { id: 'assigned', text: 'Assigned' },
    { id: 'post_window', text: 'Post-Window' },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">
          Invoice Management
        </h1>
        <Button
          kind="primary"
          size="sm"
          renderIcon={Add}
          onClick={() => setCreateModalOpen(true)}
        >
          Create Invoice
        </Button>
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load invoices"
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
                    id="invoice-status-filter"
                    titleText=""
                    label="Status"
                    items={STATUS_OPTIONS}
                    itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
                    selectedItem={STATUS_OPTIONS.find((s) => s.id === statusFilter) ?? STATUS_OPTIONS[0]}
                    onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) => {
                      setStatusFilter(selectedItem?.id ?? 'all');
                      setPage(1);
                    }}
                    size="sm"
                  />
                  <Dropdown
                    id="invoice-flow-filter"
                    titleText=""
                    label="Billing Flow"
                    items={FLOW_OPTIONS}
                    itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
                    selectedItem={FLOW_OPTIONS.find((f) => f.id === flowFilter) ?? FLOW_OPTIONS[0]}
                    onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) => {
                      setFlowFilter(selectedItem?.id ?? 'all');
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
                        Loading invoices...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : invoices.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center">
                        <Receipt size={48} className="mx-auto mb-4 text-text-secondary" />
                        <p className="text-lg font-medium text-text-primary">
                          No invoices found
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tRows.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const invoice = invoices.find((inv) => inv.id === row.id);
                    const actions = invoice ? getAvailableActions(invoice.status) : [];
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => {
                          if (cell.info.header === 'status') {
                            return (
                              <TableCell key={cell.id}>
                                <StatusTag type={statusColor(cell.value as string)}>
                                  {(cell.value as string).replace('_', ' ')}
                                </StatusTag>
                              </TableCell>
                            );
                          }
                          if (cell.info.header === 'billingFlow') {
                            return (
                              <TableCell key={cell.id}>
                                <Tag type="gray" size="sm">
                                  {billingFlowLabel(cell.value as string)}
                                </Tag>
                              </TableCell>
                            );
                          }
                          if (cell.info.header === 'totalAmount') {
                            return (
                              <TableCell key={cell.id}>
                                {formatPrice(cell.value as number)}
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
                                  <Button kind="ghost" size="sm" href={`/platform/invoices/${row.id}`}>
                                    View
                                  </Button>
                                  {actions.includes('finalize') && (
                                    <Button
                                      kind="primary"
                                      size="sm"
                                      onClick={() => handleInvoiceAction(finalizeAction, row.id, 'finalized')}
                                      disabled={finalizeAction.isPending}
                                    >
                                      Finalize
                                    </Button>
                                  )}
                                  {actions.includes('send') && (
                                    <Button
                                      kind="primary"
                                      size="sm"
                                      onClick={() => handleInvoiceAction(sendAction, row.id, 'sent')}
                                      disabled={sendAction.isPending}
                                    >
                                      Send
                                    </Button>
                                  )}
                                  {actions.includes('void') && (
                                    <Button
                                      kind="danger--ghost"
                                      size="sm"
                                      onClick={() => handleInvoiceAction(voidAction, row.id, 'voided')}
                                      disabled={voidAction.isPending}
                                    >
                                      Void
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

      {/* Create Invoice Modal */}
      <Modal
        open={createModalOpen}
        modalHeading="Create Draft Invoice"
        primaryButtonText="Create"
        secondaryButtonText="Cancel"
        onRequestSubmit={handleCreate}
        onRequestClose={() => {
          setCreateModalOpen(false);
          setNewCompanyId('');
          setNewBillingFlow('assigned');
        }}
        primaryButtonDisabled={!newCompanyId.trim() || createInvoice.isPending}
      >
        <div className="flex flex-col gap-4">
          <TextInput
            id="invoice-company-id"
            labelText="Company ID"
            placeholder="Enter the target company's UUID"
            value={newCompanyId}
            onChange={(e) => setNewCompanyId(e.target.value)}
            required
          />
          <Dropdown
            id="invoice-billing-flow"
            titleText="Billing Flow"
            label="Select billing flow"
            items={CREATE_FLOW_OPTIONS}
            itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
            selectedItem={CREATE_FLOW_OPTIONS.find((f) => f.id === newBillingFlow) ?? CREATE_FLOW_OPTIONS[0]}
            onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) =>
              setNewBillingFlow(selectedItem?.id ?? 'assigned')
            }
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
