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

import type { SizeDistribution as SizeDistributionData } from '@/types/analytics';

interface SizeDistributionProps {
  data: SizeDistributionData[];
}

const headers = [
  { key: 'size', header: 'Size' },
  { key: 'count', header: 'Count' },
  { key: 'percentage', header: 'Percentage' },
];

export function SizeDistribution({ data }: SizeDistributionProps) {
  if (data.length === 0) {
    return (
      <InlineNotification
        kind="info"
        title="No data"
        subtitle="No size distribution data available for the selected period."
        lowContrast
        hideCloseButton
      />
    );
  }

  const sorted = [...data].sort((a, b) => b.count - a.count);

  const rows = sorted.map((item) => ({
    id: item.size,
    size: item.size,
    count: item.count.toLocaleString(),
    percentage: `${item.percentage.toFixed(1)}%`,
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
