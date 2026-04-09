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

import type { CompanyRevenue } from '@/types/analytics';

interface RevenueByCompanyTableProps {
  data: CompanyRevenue[];
}

const currencyFormat = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

const headers = [
  { key: 'companyName', header: 'Company' },
  { key: 'totalRevenue', header: 'Total Revenue' },
  { key: 'invoiceCount', header: 'Invoice Count' },
];

export function RevenueByCompanyTable({ data }: RevenueByCompanyTableProps) {
  if (data.length === 0) {
    return (
      <InlineNotification
        kind="info"
        title="No data"
        subtitle="No revenue data available for the selected period."
        lowContrast
        hideCloseButton
      />
    );
  }

  const sorted = [...data].sort((a, b) => b.totalRevenue - a.totalRevenue);

  const rows = sorted.map((item) => ({
    id: item.companyId,
    companyName: item.companyName,
    totalRevenue: currencyFormat.format(item.totalRevenue),
    invoiceCount: item.invoiceCount.toLocaleString(),
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
