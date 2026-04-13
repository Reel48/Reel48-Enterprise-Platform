'use client';

import { Tile } from '@carbon/react';
import { Idea } from '@carbon/react/icons';

export default function InsideReel48Page() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold" style={{ color: 'var(--cds-text-primary)' }}>
        InsideReel48+
      </h1>
      <Tile className="py-12 text-center">
        <div className="flex flex-col items-center gap-4">
          <Idea size={48} style={{ fill: 'var(--cds-icon-secondary)' }} />
          <p className="text-lg font-medium" style={{ color: 'var(--cds-text-primary)' }}>
            Coming Soon
          </p>
          <p className="text-sm" style={{ color: 'var(--cds-text-secondary)' }}>
            Internal resources and company news will be available here.
          </p>
        </div>
      </Tile>
    </div>
  );
}
