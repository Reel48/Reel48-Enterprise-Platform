'use client';

import { useState } from 'react';
import {
  Button,
  DataTable,
  Dropdown,
  InlineNotification,
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
  ToastNotification,
} from '@carbon/react';
import { Catalog as CatalogIcon } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Catalog, CatalogStatus } from '@/types/catalogs';

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
  { key: 'productCount', header: 'Products' },
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

  const { data, isLoading, isError } = usePlatformCatalogs(page, perPage, statusFilter);
  const approveAction = useCatalogAction('approve');
  const rejectAction = useCatalogAction('reject');
  const activateAction = useCatalogAction('activate');
  const closeAction = useCatalogAction('close');

  const catalogs = data?.data ?? [];
  const total = data?.total ?? 0;

  const rows = catalogs.map((c) => ({
    id: c.id,
    name: c.name,
    companyName: c.companyName ?? '—',
    status: c.status,
    paymentModel: c.paymentModel === 'self_service' ? 'Self-Service' : 'Invoice After Close',
    productCount: c.productCount,
    createdAt: c.createdAt,
  }));

  const handleAction = (action: ReturnType<typeof useCatalogAction>, id: string, label: string) => {
    action.mutate(id, {
      onSuccess: () => {
        setToast({ kind: 'success', message: `Catalog ${label} successfully` });
        setTimeout(() => setToast(null), 3000);
      },
      onError: () => {
        setToast({ kind: 'error', message: `Failed to ${label.toLowerCase()} catalog` });
        setTimeout(() => setToast(null), 3000);
      },
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

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-text-primary">
        Catalog Management
      </h1>

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
                                <Tag type={statusColor(cell.value as string)} size="sm">
                                  {cell.value as string}
                                </Tag>
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
