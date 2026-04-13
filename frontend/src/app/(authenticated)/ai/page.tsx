'use client';

import { Tile } from '@carbon/react';
import { AiGenerate } from '@carbon/react/icons';

export default function Reel48AIPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold" style={{ color: 'var(--cds-text-primary)' }}>
        Reel48+ AI
      </h1>
      <Tile className="py-12 text-center">
        <div className="flex flex-col items-center gap-4">
          <AiGenerate size={48} style={{ fill: 'var(--cds-icon-secondary)' }} />
          <p className="text-lg font-medium" style={{ color: 'var(--cds-text-primary)' }}>
            Coming Soon
          </p>
          <p className="text-sm" style={{ color: 'var(--cds-text-secondary)' }}>
            AI-powered insights and recommendations will be available here.
          </p>
        </div>
      </Tile>
    </div>
  );
}
