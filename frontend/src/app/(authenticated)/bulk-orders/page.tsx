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
} from '@carbon/react';
import { Add, GroupResource } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/lib/auth/hooks';
import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';
import type { BulkOrder } from '@/types/bulk-orders';
import type { UserRole } from '@/types/auth';

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
    case 'delivered':
      return 'green';
    case 'shipped':
    case 'processing':
      return 'blue';
    case 'approved':
      return 'teal';
    case 'pending':
    case 'submitted':
    case 'draft':
      return 'purple';
    case 'cancelled':
      return 'red';
    default:
      return 'gray';
  }
}

const CAN_CREATE_BULK: UserRole[] = [
  'reel48_admin',
  'corporate_admin',
  'sub_brand_admin',
  'regional_manager',
];

const STATUS_OPTIONS = [
  { id: 'all', text: 'All Statuses' },
  { id: 'draft', text: 'Draft' },
  { id: 'submitted', text: 'Submitted' },
  { id: 'approved', text: 'Approved' },
  { id: 'processing', text: 'Processing' },
  { id: 'shipped', text: 'Shipped' },
  { id: 'delivered', text: 'Delivered' },
  { id: 'cancelled', text: 'Cancelled' },
];

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useBulkOrders(page: number, perPage: number, status: string | undefined) {
  return useQuery({
    queryKey: ['bulk-orders', page, perPage, status],
    queryFn: async () => {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (status && status !== 'all') {
        params.status = status;
      }
      const res = await api.get<BulkOrder[]>('/api/v1/bulk_orders/', params);
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

function useSubmitBulkOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/bulk_orders/${id}/submit`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bulk-orders'] });
    },
  });
}

function useApproveBulkOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/bulk_orders/${id}/approve`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bulk-orders'] });
    },
  });
}

function useCancelBulkOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/bulk_orders/${id}/cancel`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bulk-orders'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Table config
// ---------------------------------------------------------------------------

const headers = [
  { key: 'title', header: 'Title' },
  { key: 'status', header: 'Status' },
  { key: 'totalItems', header: 'Items' },
  { key: 'totalAmount', header: 'Amount' },
  { key: 'createdBy', header: 'Created By' },
  { key: 'createdAt', header: 'Date' },
  { key: 'actions', header: '' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BulkOrdersPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState('all');

  const role = user?.tenantContext.role ?? 'employee';
  const canCreate = CAN_CREATE_BULK.includes(role);

  const { data, isLoading, isError } = useBulkOrders(page, perPage, statusFilter);
  const submitOrder = useSubmitBulkOrder();
  const approveOrder = useApproveBulkOrder();
  const cancelOrder = useCancelBulkOrder();

  const bulkOrders = data?.data ?? [];
  const total = data?.total ?? 0;

  const rows = bulkOrders.map((bo) => ({
    id: bo.id,
    title: bo.title ?? 'Bulk Order',
    status: bo.status,
    totalItems: bo.totalItems,
    totalAmount: bo.totalAmount,
    createdBy: bo.createdBy ?? '—',
    createdAt: bo.createdAt,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">
          Bulk Orders
        </h1>
        {canCreate && (
          <Button kind="primary" size="sm" href="/bulk-orders/new" renderIcon={Add}>
            Create Bulk Order
          </Button>
        )}
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load bulk orders"
          hideCloseButton
        />
      )}

      <DataTable rows={rows} headers={headers} isSortable={false}>
        {({ rows: tableRows, headers: tableHeaders, getHeaderProps, getRowProps, getTableProps }) => (
          <TableContainer>
            <TableToolbar>
              <TableToolbarContent>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-medium" style={{ color: 'var(--cds-text-secondary)' }}>Filter:</span>
                  <Dropdown
                    id="bulk-status-filter"
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
                  {tableHeaders.map((header) => {
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
                    <TableCell colSpan={headers.length}>
                      <div className="py-8 text-center text-text-secondary">
                        Loading bulk orders...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : bulkOrders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={headers.length}>
                      <div className="py-8 text-center">
                        <GroupResource size={48} className="mx-auto mb-4 text-text-secondary" />
                        <p className="text-lg font-medium text-text-primary">
                          No bulk orders found
                        </p>
                        <p className="text-sm text-text-secondary mt-1">
                          {canCreate
                            ? 'Create a bulk order to get started'
                            : 'No bulk orders have been created yet'}
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRows.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const bo = bulkOrders.find((b) => b.id === row.id);
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
                                  <Button kind="ghost" size="sm" href={`/bulk-orders/${row.id}`}>
                                    View
                                  </Button>
                                  {bo?.status === 'draft' && (
                                    <Button
                                      kind="primary"
                                      size="sm"
                                      onClick={() => submitOrder.mutate(row.id)}
                                      disabled={submitOrder.isPending}
                                    >
                                      Submit
                                    </Button>
                                  )}
                                  {bo?.status === 'submitted' && canCreate && (
                                    <Button
                                      kind="primary"
                                      size="sm"
                                      onClick={() => approveOrder.mutate(row.id)}
                                      disabled={approveOrder.isPending}
                                    >
                                      Approve
                                    </Button>
                                  )}
                                  {(bo?.status === 'draft' || bo?.status === 'submitted') && (
                                    <Button
                                      kind="danger--ghost"
                                      size="sm"
                                      onClick={() => cancelOrder.mutate(row.id)}
                                      disabled={cancelOrder.isPending}
                                    >
                                      Cancel
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
          onChange={({ page: newPage, pageSize }: { page: number; pageSize: number }) => {
            setPage(newPage);
            setPerPage(pageSize);
          }}
        />
      )}
    </div>
  );
}
