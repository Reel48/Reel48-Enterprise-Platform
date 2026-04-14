'use client';

import { useState } from 'react';
import {
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
} from '@carbon/react';
import { Receipt } from '@carbon/react/icons';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

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

function formatDate(dateString: string | null): string {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function statusColor(status: string): 'teal' | 'blue' | 'purple' | 'gray' | 'green' | 'red' {
  switch (status) {
    case 'paid': return 'green';
    case 'sent': return 'blue';
    case 'finalized': return 'teal';
    case 'draft': return 'purple';
    case 'payment_failed': case 'voided': return 'red';
    default: return 'gray';
  }
}

function billingFlowLabel(flow: string): string {
  switch (flow) {
    case 'assigned': return 'Assigned';
    case 'self_service': return 'Self-Service';
    case 'post_window': return 'Post-Window';
    case 'linked': return 'Linked';
    default: return flow;
  }
}

const STATUS_FILTER_OPTIONS = [
  { id: 'all', text: 'All Statuses' },
  { id: 'draft', text: 'Draft' },
  { id: 'finalized', text: 'Finalized' },
  { id: 'sent', text: 'Sent' },
  { id: 'paid', text: 'Paid' },
  { id: 'payment_failed', text: 'Payment Failed' },
  { id: 'voided', text: 'Voided' },
];

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useInvoices(page: number, perPage: number, statusFilter: string) {
  const params: Record<string, string> = {
    page: String(page),
    per_page: String(perPage),
  };
  if (statusFilter !== 'all') params.status = statusFilter;

  return useQuery({
    queryKey: ['invoices', page, perPage, statusFilter],
    queryFn: async () => {
      const res = await api.get<Invoice[]>('/api/v1/invoices/', params);
      return res;
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function InvoicesPage() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState('all');

  const { data, isLoading, isError } = useInvoices(page, perPage, statusFilter);

  const invoices = data?.data ?? [];
  const total = Number(data?.meta?.total ?? 0);

  const tableHeaders = [
    { key: 'invoiceNumber', header: 'Invoice #' },
    { key: 'status', header: 'Status' },
    { key: 'billingFlow', header: 'Billing Flow' },
    { key: 'totalAmount', header: 'Amount' },
    { key: 'dueDate', header: 'Due Date' },
    { key: 'createdAt', header: 'Created' },
  ];

  const tableRows = invoices.map((inv) => ({
    id: inv.id,
    invoiceNumber: inv.invoiceNumber ?? 'Draft',
    status: inv.status,
    billingFlow: inv.billingFlow,
    totalAmount: inv.totalAmount,
    dueDate: inv.dueDate,
    createdAt: inv.createdAt,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Receipt size={24} className="text-interactive" />
        <h1 className="text-2xl font-semibold text-text-primary">Invoices</h1>
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load invoices"
          subtitle="Please try refreshing the page."
          hideCloseButton
        />
      )}

      <DataTable rows={tableRows} headers={tableHeaders} isSortable={false}>
        {({ rows: tableRowsProp, headers, getHeaderProps, getRowProps, getTableProps }) => (
          <TableContainer>
            <TableToolbar>
              <TableToolbarContent>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-medium" style={{ color: 'var(--cds-text-secondary)' }}>Filter:</span>
                  <Dropdown
                    id="status-filter"
                    titleText=""
                    label="Select status"
                    items={STATUS_FILTER_OPTIONS}
                    itemToString={(item) => item?.text ?? ''}
                    initialSelectedItem={STATUS_FILTER_OPTIONS[0]}
                    onChange={({ selectedItem }) => {
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
                      <div className="py-8 text-center text-text-secondary">Loading invoices...</div>
                    </TableCell>
                  </TableRow>
                ) : tableRowsProp.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">No invoices found.</div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRowsProp.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const original = invoices.find((inv) => inv.id === row.id);
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'invoiceNumber' && original ? (
                              <Link
                                href={`/invoices/${original.id}`}
                                className="text-link-primary hover:underline"
                              >
                                {original.invoiceNumber ?? 'Draft'}
                              </Link>
                            ) : cell.info.header === 'status' && original ? (
                              <StatusTag type={statusColor(original.status)}>
                                {original.status.replace('_', ' ')}
                              </StatusTag>
                            ) : cell.info.header === 'billingFlow' && original ? (
                              <Tag type="gray" size="sm">
                                {billingFlowLabel(original.billingFlow)}
                              </Tag>
                            ) : cell.info.header === 'totalAmount' && original ? (
                              formatPrice(original.totalAmount)
                            ) : cell.info.header === 'dueDate' && original ? (
                              formatDate(original.dueDate)
                            ) : cell.info.header === 'createdAt' && original ? (
                              formatDate(original.createdAt)
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
    </div>
  );
}
