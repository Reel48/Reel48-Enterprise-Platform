'use client';

import { Tag } from '@carbon/react';

import { useAuth } from '@/lib/auth/hooks';

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) return null;

  const { tenantContext } = user;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-text-primary">
        Welcome, {user.fullName}
      </h1>

      <div className="flex flex-wrap gap-2">
        <Tag type="teal">{tenantContext.role.replace(/_/g, ' ')}</Tag>
        {tenantContext.companyId && (
          <Tag type="gray">Company: {tenantContext.companyId}</Tag>
        )}
        {tenantContext.subBrandId && (
          <Tag type="gray">Sub-Brand: {tenantContext.subBrandId}</Tag>
        )}
      </div>

      <p className="text-text-secondary">
        Dashboard coming in Module 2+
      </p>
    </div>
  );
}
