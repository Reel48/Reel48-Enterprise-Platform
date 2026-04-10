import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TopProductsTable } from '@/components/features/analytics';
import type { TopProduct } from '@/types/analytics';

const mockProducts: TopProduct[] = [
  {
    productId: 'prod-001',
    productName: 'Premium Polo Shirt',
    productSku: 'SKU-POLO-001',
    totalQuantity: 200,
    totalRevenue: 5000.0,
  },
  {
    productId: 'prod-002',
    productName: 'Classic T-Shirt',
    productSku: 'SKU-TEE-002',
    totalQuantity: 150,
    totalRevenue: 3000.0,
  },
  {
    productId: 'prod-003',
    productName: 'Fleece Jacket',
    productSku: 'SKU-JKT-003',
    totalQuantity: 80,
    totalRevenue: 4000.0,
  },
];

describe('TopProductsTable', () => {
  it('renders product rows with correct rank ordering', () => {
    render(<TopProductsTable data={mockProducts} />);

    // Check headers
    expect(screen.getByText('Rank')).toBeInTheDocument();
    expect(screen.getByText('Product Name')).toBeInTheDocument();
    expect(screen.getByText('SKU')).toBeInTheDocument();
    expect(screen.getByText('Quantity')).toBeInTheDocument();
    expect(screen.getByText('Revenue')).toBeInTheDocument();

    // Check product data with ranks
    expect(screen.getByText('Premium Polo Shirt')).toBeInTheDocument();
    expect(screen.getByText('SKU-POLO-001')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText('$5,000.00')).toBeInTheDocument();

    expect(screen.getByText('Classic T-Shirt')).toBeInTheDocument();
    expect(screen.getByText('Fleece Jacket')).toBeInTheDocument();

    // Check rank numbers
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows empty state when no products', () => {
    render(<TopProductsTable data={[]} />);

    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(
      screen.getByText('No product data available for the selected period.'),
    ).toBeInTheDocument();

    // Table headers should NOT be present
    expect(screen.queryByText('Rank')).not.toBeInTheDocument();
  });

  it('respects limit prop', () => {
    render(<TopProductsTable data={mockProducts} limit={2} />);

    expect(screen.getByText('Premium Polo Shirt')).toBeInTheDocument();
    expect(screen.getByText('Classic T-Shirt')).toBeInTheDocument();
    expect(screen.queryByText('Fleece Jacket')).not.toBeInTheDocument();
  });
});
