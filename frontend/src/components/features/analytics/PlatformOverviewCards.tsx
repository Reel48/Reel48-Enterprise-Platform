'use client';

import { Tile } from '@carbon/react';
import {
  Enterprise,
  Store,
  UserMultiple,
  ShoppingCart,
  Currency,
  Catalog,
} from '@carbon/react/icons';

import type { PlatformOverview } from '@/types/analytics';

interface PlatformOverviewCardsProps {
  data: PlatformOverview;
}

const currencyFormat = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

export function PlatformOverviewCards({ data }: PlatformOverviewCardsProps) {
  const cards = [
    {
      label: 'Total Companies',
      value: data.totalCompanies.toLocaleString(),
      Icon: Enterprise,
    },
    {
      label: 'Total Sub-Brands',
      value: data.totalSubBrands.toLocaleString(),
      Icon: Store,
    },
    {
      label: 'Total Users',
      value: data.totalUsers.toLocaleString(),
      Icon: UserMultiple,
    },
    {
      label: 'Total Orders',
      value: data.totalOrders.toLocaleString(),
      Icon: ShoppingCart,
    },
    {
      label: 'Total Revenue',
      value: currencyFormat.format(data.totalRevenue),
      Icon: Currency,
    },
    {
      label: 'Active Catalogs',
      value: data.activeCatalogs.toLocaleString(),
      Icon: Catalog,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
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
