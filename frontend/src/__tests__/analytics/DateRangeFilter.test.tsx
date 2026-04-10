import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { DateRangeFilter } from '@/components/features/analytics';

describe('DateRangeFilter', () => {
  it('renders two date inputs', () => {
    const onDateChange = vi.fn();
    render(<DateRangeFilter onDateChange={onDateChange} />);

    expect(screen.getByLabelText('Start date')).toBeInTheDocument();
    expect(screen.getByLabelText('End date')).toBeInTheDocument();
  });

  it('renders with placeholder text', () => {
    const onDateChange = vi.fn();
    render(<DateRangeFilter onDateChange={onDateChange} />);

    const inputs = screen.getAllByPlaceholderText('mm/dd/yyyy');
    expect(inputs).toHaveLength(2);
  });

  it('accepts default date range props', () => {
    const onDateChange = vi.fn();
    const start = new Date(2026, 2, 10); // March 10, 2026
    const end = new Date(2026, 3, 9); // April 9, 2026

    render(
      <DateRangeFilter
        onDateChange={onDateChange}
        defaultStartDate={start}
        defaultEndDate={end}
      />,
    );

    expect(screen.getByLabelText('Start date')).toBeInTheDocument();
    expect(screen.getByLabelText('End date')).toBeInTheDocument();
  });
});
