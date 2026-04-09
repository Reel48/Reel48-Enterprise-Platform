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

import type { TopProduct } from '@/types/analytics';

interface TopProductsTableProps {
  data: TopProduct[];
  limit?: number;
}

const currencyFormat = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

const headers = [
  { key: 'rank', header: 'Rank' },
  { key: 'productName', header: 'Product Name' },
  { key: 'productSku', header: 'SKU' },
  { key: 'totalQuantity', header: 'Quantity' },
  { key: 'totalRevenue', header: 'Revenue' },
];

export function TopProductsTable({ data, limit }: TopProductsTableProps) {
  const items = limit ? data.slice(0, limit) : data;

  if (items.length === 0) {
    return (
      <InlineNotification
        kind="info"
        title="No data"
        subtitle="No product data available for the selected period."
        lowContrast
        hideCloseButton
      />
    );
  }

  const rows = items.map((item, index) => ({
    id: item.productId,
    rank: index + 1,
    productName: item.productName,
    productSku: item.productSku,
    totalQuantity: item.totalQuantity.toLocaleString(),
    totalRevenue: currencyFormat.format(item.totalRevenue),
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
