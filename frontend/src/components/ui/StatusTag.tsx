'use client';

import { Tag } from '@carbon/react';

type TagColor = 'green' | 'red' | 'teal' | 'blue' | 'purple' | 'gray';

interface StatusTagProps {
  type: TagColor;
  children: React.ReactNode;
  size?: 'sm' | 'md';
}

/**
 * Status tag with a small glowing dot indicator before the label text.
 * Wraps Carbon's Tag component with the dot + label pattern.
 */
export function StatusTag({ type, children, size = 'sm' }: StatusTagProps) {
  return (
    <Tag type={type} size={size}>
      <span className={`status-dot status-dot--${type}`}>
        {children}
      </span>
    </Tag>
  );
}
