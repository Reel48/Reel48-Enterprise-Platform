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

import type { SubBrandSpend } from '@/types/analytics';

interface SpendBySubBrandTableProps {
  data: SubBrandSpend[];
}

const currencyFormat = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

const headers = [
  { key: 'subBrandName', header: 'Sub-Brand' },
  { key: 'totalSpend', header: 'Total Spend' },
  { key: 'orderCount', header: 'Order Count' },
];

export function SpendBySubBrandTable({ data }: SpendBySubBrandTableProps) {
  if (data.length === 0) {
    return (
      <InlineNotification
        kind="info"
        title="No data"
        subtitle="No sub-brand spend data available for the selected period."
        lowContrast
        hideCloseButton
      />
    );
  }

  const rows = data.map((item) => ({
    id: item.subBrandId,
    subBrandName: item.subBrandName,
    totalSpend: currencyFormat.format(item.totalSpend),
    orderCount: item.orderCount,
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
