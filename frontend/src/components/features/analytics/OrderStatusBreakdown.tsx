'use client';

import {
  DataTable,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  InlineNotification,
} from '@carbon/react';

import type { OrderStatusBreakdown as OrderStatusBreakdownData } from '@/types/analytics';

interface OrderStatusBreakdownProps {
  data: OrderStatusBreakdownData[];
}

const headers = [
  { key: 'status', header: 'Status' },
  { key: 'count', header: 'Count' },
  { key: 'orderType', header: 'Order Type' },
];

function formatStatus(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ');
}

function formatOrderType(type: string): string {
  return type === 'individual' ? 'Individual' : 'Bulk';
}

export function OrderStatusBreakdown({ data }: OrderStatusBreakdownProps) {
  if (data.length === 0) {
    return (
      <InlineNotification
        kind="info"
        title="No data"
        subtitle="No order status data available for the selected period."
        lowContrast
        hideCloseButton
      />
    );
  }

  const rows = data.map((item, index) => ({
    id: `${item.orderType}-${item.status}-${index}`,
    status: formatStatus(item.status),
    count: item.count.toLocaleString(),
    orderType: formatOrderType(item.orderType),
  }));

  return (
    <DataTable rows={rows} headers={headers}>
      {({ rows: tableRows, headers: tableHeaders, getTableProps, getHeaderProps, getRowProps }) => (
        <TableContainer>
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
              {tableRows.map((row) => {
                const { key: rowKey, ...rowProps } = getRowProps({ row });
                return (
                <TableRow key={String(rowKey)} {...rowProps}>
                  {row.cells.map((cell) => (
                    <TableCell key={cell.id}>{cell.value}</TableCell>
                  ))}
                </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </DataTable>
  );
}
