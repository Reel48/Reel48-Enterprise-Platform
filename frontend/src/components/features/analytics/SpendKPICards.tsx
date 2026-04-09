'use client';

import { Tile } from '@carbon/react';

import type { SpendSummary } from '@/types/analytics';

interface SpendKPICardsProps {
  data: SpendSummary;
}

const currencyFormat = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

export function SpendKPICards({ data }: SpendKPICardsProps) {
  const cards = [
    { label: 'Total Spend', value: currencyFormat.format(data.totalSpend) },
    { label: 'Order Count', value: data.orderCount.toLocaleString() },
    { label: 'Avg Order Value', value: currencyFormat.format(data.averageOrderValue) },
    { label: 'Individual Orders', value: currencyFormat.format(data.individualOrderSpend) },
    { label: 'Bulk Orders', value: currencyFormat.format(data.bulkOrderSpend) },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
      {cards.map((card) => (
        <Tile key={card.label}>
          <p className="text-sm text-text-secondary mb-1">{card.label}</p>
          <p className="text-2xl font-semibold">{card.value}</p>
        </Tile>
      ))}
    </div>
  );
}
