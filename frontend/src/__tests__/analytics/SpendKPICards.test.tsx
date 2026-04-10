import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SpendKPICards } from '@/components/features/analytics';
import type { SpendSummary } from '@/types/analytics';

const mockData: SpendSummary = {
  totalSpend: 25000.0,
  orderCount: 150,
  averageOrderValue: 166.67,
  individualOrderSpend: 15000.0,
  bulkOrderSpend: 10000.0,
};

describe('SpendKPICards', () => {
  it('renders correctly with valid data showing formatted currency', () => {
    render(<SpendKPICards data={mockData} />);

    expect(screen.getByText('Total Spend')).toBeInTheDocument();
    expect(screen.getByText('$25,000.00')).toBeInTheDocument();

    expect(screen.getByText('Order Count')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();

    expect(screen.getByText('Avg Order Value')).toBeInTheDocument();
    expect(screen.getByText('$166.67')).toBeInTheDocument();

    expect(screen.getByText('Individual Orders')).toBeInTheDocument();
    expect(screen.getByText('$15,000.00')).toBeInTheDocument();

    expect(screen.getByText('Bulk Orders')).toBeInTheDocument();
    expect(screen.getByText('$10,000.00')).toBeInTheDocument();
  });

  it('handles zero values gracefully', () => {
    const zeroData: SpendSummary = {
      totalSpend: 0,
      orderCount: 0,
      averageOrderValue: 0,
      individualOrderSpend: 0,
      bulkOrderSpend: 0,
    };

    render(<SpendKPICards data={zeroData} />);

    expect(screen.getByText('Total Spend')).toBeInTheDocument();
    // $0.00 should appear for all currency fields
    const zeroAmounts = screen.getAllByText('$0.00');
    expect(zeroAmounts).toHaveLength(4);

    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('renders all five KPI cards', () => {
    render(<SpendKPICards data={mockData} />);

    const labels = [
      'Total Spend',
      'Order Count',
      'Avg Order Value',
      'Individual Orders',
      'Bulk Orders',
    ];

    labels.forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });
});
