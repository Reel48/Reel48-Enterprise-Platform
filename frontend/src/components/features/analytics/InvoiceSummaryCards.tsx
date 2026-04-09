'use client';

import { Tile } from '@carbon/react';

import type { InvoiceSummary } from '@/types/analytics';

interface InvoiceSummaryCardsProps {
  data: InvoiceSummary;
}

const currencyFormat = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

export function InvoiceSummaryCards({ data }: InvoiceSummaryCardsProps) {
  const cards = [
    { label: 'Total Invoiced', value: currencyFormat.format(data.totalInvoiced) },
    {
      label: 'Total Paid',
      value: currencyFormat.format(data.totalPaid),
      accent: 'text-support-success',
    },
    {
      label: 'Total Outstanding',
      value: currencyFormat.format(data.totalOutstanding),
      accent: 'text-accent-saffron',
    },
    { label: 'Invoice Count', value: data.invoiceCount.toLocaleString() },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((card) => (
        <Tile key={card.label}>
          <p className="text-sm text-text-secondary mb-1">{card.label}</p>
          <p className={`text-2xl font-semibold ${card.accent ?? ''}`}>
            {card.value}
          </p>
        </Tile>
      ))}
    </div>
  );
}
