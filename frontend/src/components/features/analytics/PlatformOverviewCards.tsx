'use client';

import { Tile } from '@carbon/react';
import { Enterprise, UserMultiple } from '@carbon/react/icons';

import type { PlatformOverview } from '@/types/analytics';

interface PlatformOverviewCardsProps {
  data: PlatformOverview;
}

export function PlatformOverviewCards({ data }: PlatformOverviewCardsProps) {
  const cards = [
    {
      label: 'Total Companies',
      value: data.totalCompanies.toLocaleString(),
      Icon: Enterprise,
    },
    {
      label: 'Total Users',
      value: data.totalUsers.toLocaleString(),
      Icon: UserMultiple,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {cards.map((card) => (
        <Tile key={card.label}>
          <div className="flex items-start gap-3">
            <card.Icon size={24} className="text-interactive mt-0.5 shrink-0" />
            <div>
              <p className="text-sm text-text-secondary mb-1">{card.label}</p>
              <p className="text-2xl font-semibold">{card.value}</p>
            </div>
          </div>
        </Tile>
      ))}
    </div>
  );
}
