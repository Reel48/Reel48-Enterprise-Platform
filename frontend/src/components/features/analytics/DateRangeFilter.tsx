'use client';

import { useCallback, useState } from 'react';
import { DatePicker, DatePickerInput } from '@carbon/react';

interface DateRangeFilterProps {
  onDateChange: (startDate: string | undefined, endDate: string | undefined) => void;
  defaultStartDate?: Date;
  defaultEndDate?: Date;
}

function formatDateToISO(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function DateRangeFilter({
  onDateChange,
  defaultStartDate,
  defaultEndDate,
}: DateRangeFilterProps) {
  const [startDate, setStartDate] = useState<Date | undefined>(defaultStartDate);
  const [endDate, setEndDate] = useState<Date | undefined>(defaultEndDate);

  const handleChange = useCallback(
    (dates: Date[]) => {
      const [start, end] = dates;
      setStartDate(start);
      setEndDate(end);

      if (start && end) {
        onDateChange(formatDateToISO(start), formatDateToISO(end));
      } else if (!start && !end) {
        onDateChange(undefined, undefined);
      }
    },
    [onDateChange],
  );

  return (
    <DatePicker
      datePickerType="range"
      onChange={handleChange}
      value={[startDate ?? '', endDate ?? '']}
    >
      <DatePickerInput
        id="analytics-start-date"
        labelText="Start date"
        placeholder="mm/dd/yyyy"
        size="md"
      />
      <DatePickerInput
        id="analytics-end-date"
        labelText="End date"
        placeholder="mm/dd/yyyy"
        size="md"
      />
    </DatePicker>
  );
}
