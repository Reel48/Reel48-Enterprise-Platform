'use client';

import { Tile } from '@carbon/react';

import type { ApprovalMetrics } from '@/types/analytics';

interface ApprovalMetricsCardsProps {
  data: ApprovalMetrics;
}

export function ApprovalMetricsCards({ data }: ApprovalMetricsCardsProps) {
  const approvalRateFormatted = `${(data.approvalRate * 100).toFixed(1)}%`;
  const avgTimeFormatted =
    data.avgApprovalTimeHours !== null
      ? `${data.avgApprovalTimeHours.toFixed(1)}h`
      : 'N/A';

  const cards = [
    {
      label: 'Pending',
      value: data.pendingCount.toLocaleString(),
      accent: 'text-accent-saffron',
    },
    {
      label: 'Approved',
      value: data.approvedCount.toLocaleString(),
      accent: 'text-support-success',
    },
    {
      label: 'Rejected',
      value: data.rejectedCount.toLocaleString(),
      accent: 'text-support-error',
    },
    { label: 'Approval Rate', value: approvalRateFormatted },
    { label: 'Avg Approval Time', value: avgTimeFormatted },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
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
