'use client';

import { useState } from 'react';
import Link from 'next/link';
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
  Tile,
} from '@carbon/react';
import { ShoppingCart } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/lib/auth/hooks';
import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';
import type { Order, OrderStatus } from '@/types/orders';
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
      return 'purple';
    case 'cancelled':
      return 'red';
    default:
      return 'gray';
  }
}

const MANAGER_AND_ABOVE: UserRole[] = [
  'reel48_admin',
  'corporate_admin',
  'sub_brand_admin',
  'regional_manager',
];

const STATUS_OPTIONS = [
  { id: 'all', text: 'All Statuses' },
  { id: 'pending', text: 'Pending' },
  { id: 'approved', text: 'Approved' },
  { id: 'processing', text: 'Processing' },
  { id: 'shipped', text: 'Shipped' },
  { id: 'delivered', text: 'Delivered' },
  { id: 'cancelled', text: 'Cancelled' },
];

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useOrders(
  page: number,
  perPage: number,
  status: string | undefined,
  isManager: boolean,
) {
  const endpoint = isManager ? '/api/v1/orders/' : '/api/v1/orders/my/';
  return useQuery({
    queryKey: ['orders', page, perPage, status, isManager],
    queryFn: async () => {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (status && status !== 'all') {
        params.status = status;
      }
      const res = await api.get<Order[]>(endpoint, params);
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

function useCancelOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      await api.post(`/api/v1/orders/${orderId}/cancel`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Table config
// ---------------------------------------------------------------------------

const headers = [
  { key: 'orderNumber', header: 'Order #' },
  { key: 'status', header: 'Status' },
  { key: 'totalAmount', header: 'Amount' },
  { key: 'subtotal', header: 'Subtotal' },
  { key: 'createdAt', header: 'Date' },
  { key: 'actions', header: '' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OrdersPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState('all');
  const cancelOrder = useCancelOrder();

  const role = user?.tenantContext.role ?? 'employee';
  const isManager = MANAGER_AND_ABOVE.includes(role);

  const { data, isLoading, isError } = useOrders(page, perPage, statusFilter, isManager);

  const orders = data?.data ?? [];
  const total = data?.total ?? 0;

  const rows = orders.map((order) => ({
    id: order.id,
    orderNumber: order.orderNumber,
    status: order.status,
    totalAmount: order.totalAmount,
    subtotal: order.subtotal,
    createdAt: order.createdAt,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">
          {isManager ? 'All Orders' : 'My Orders'}
        </h1>
        <Button kind="primary" size="sm" href="/catalog">
          Browse Catalog
        </Button>
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load orders"
          subtitle="Please try refreshing the page."
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
                    id="status-filter"
                    titleText=""
                    label="All Statuses"
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
                        Loading orders...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={headers.length}>
                      <div className="py-8 text-center">
                        <ShoppingCart size={48} className="mx-auto mb-4 text-text-secondary" />
                        <p className="text-lg font-medium text-text-primary">No orders found</p>
                        <p className="text-sm text-text-secondary mt-1">
                          <Link href="/catalog" className="text-link-primary">
                            Browse catalogs
                          </Link>{' '}
                          to place your first order
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRows.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const order = orders.find((o) => o.id === row.id);
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
                          if (cell.info.header === 'subtotal' || cell.info.header === 'totalAmount') {
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
                                  <Button
                                    kind="ghost"
                                    size="sm"
                                    href={`/orders/${row.id}`}
                                  >
                                    View
                                  </Button>
                                  {order?.status === 'pending' && (
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
