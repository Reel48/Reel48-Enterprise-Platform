'use client';

import dynamic from 'next/dynamic';
import { Loading } from '@carbon/react';
import { ScaleTypes } from '@carbon/charts/interfaces';

import type { SpendOverTime } from '@/types/analytics';

const LineChart = dynamic(
  () => import('@carbon/charts-react').then((mod) => mod.LineChart),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-64">
        <Loading withOverlay={false} small description="Loading chart..." />
      </div>
    ),
  },
);

interface SpendOverTimeChartProps {
  data: SpendOverTime[];
  title?: string;
}

export function SpendOverTimeChart({ data, title = 'Spend Over Time' }: SpendOverTimeChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-text-secondary">
        No trend data available for the selected period.
      </div>
    );
  }

  const chartData = data.map((item) => ({
    group: 'Spend',
    date: item.period,
    value: item.totalSpend,
  }));

  const options = {
    title,
    axes: {
      bottom: {
        mapsTo: 'date',
        scaleType: ScaleTypes.LABELS,
        title: 'Period',
      },
      left: {
        mapsTo: 'value',
        scaleType: ScaleTypes.LINEAR,
        title: 'Amount ($)',
      },
    },
    color: {
      scale: {
        Spend: '#0a6b6b',
      },
    },
    curve: 'curveMonotoneX' as const,
    height: '320px',
    toolbar: {
      enabled: false,
    },
    legend: {
      enabled: false,
    },
  };

  return <LineChart data={chartData} options={options} />;
}
