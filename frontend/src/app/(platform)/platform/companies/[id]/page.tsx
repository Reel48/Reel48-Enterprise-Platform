'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  InlineNotification,
  Tag,
  TextInput,
  Tile,
  ToastNotification,
} from '@carbon/react';
import { Enterprise, Save } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Company } from '@/types/companies';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SubBrand {
  id: string;
  name: string;
  slug: string;
  isDefault: boolean;
  isActive: boolean;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useCompany(id: string) {
  return useQuery({
    queryKey: ['platform-company', id],
    queryFn: async () => {
      const res = await api.get<Company>(`/api/v1/platform/companies/${id}`);
      return res.data;
    },
  });
}

function useCompanySubBrands(companyId: string) {
  return useQuery({
    queryKey: ['platform-company-sub-brands', companyId],
    queryFn: async () => {
      const res = await api.get<SubBrand[]>(
        `/api/v1/platform/companies/${companyId}/sub_brands/`,
        { page: '1', per_page: '100' },
      );
      return res.data;
    },
  });
}

function useUpdateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Company> }) => {
      const res = await api.patch<Company>(`/api/v1/platform/companies/${id}`, data);
      return res.data;
    },
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['platform-company', id] });
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] });
    },
  });
}

function useDeactivateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/platform/companies/${id}/deactivate`);
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['platform-company', id] });
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: company, isLoading, isError } = useCompany(params.id);
  const { data: subBrands } = useCompanySubBrands(params.id);
  const updateCompany = useUpdateCompany();
  const deactivateCompany = useDeactivateCompany();

  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [initialized, setInitialized] = useState(false);
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  if (company && !initialized) {
    setEditName(company.name);
    setEditEmail(company.contactEmail ?? '');
    setEditPhone(company.contactPhone ?? '');
    setInitialized(true);
  }

  if (isLoading) {
    return (
      <div className="py-12 text-center text-text-secondary">
        Loading company...
      </div>
    );
  }

  if (isError || !company) {
    return (
      <InlineNotification
        kind="error"
        title="Failed to load company"
        subtitle="The company may not exist."
        hideCloseButton
      />
    );
  }

  const handleSave = () => {
    updateCompany.mutate(
      {
        id: params.id,
        data: {
          name: editName,
          contactEmail: editEmail || null,
          contactPhone: editPhone || null,
        },
      },
      {
        onSuccess: () => {
          setToast({ kind: 'success', message: 'Company updated' });
          setTimeout(() => setToast(null), 3000);
        },
        onError: () => {
          setToast({ kind: 'error', message: 'Failed to update company' });
          setTimeout(() => setToast(null), 3000);
        },
      },
    );
  };

  const handleDeactivate = () => {
    deactivateCompany.mutate(params.id, {
      onSuccess: () => {
        setToast({ kind: 'success', message: 'Company deactivated' });
        setTimeout(() => setToast(null), 3000);
      },
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/platform/companies">Companies</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>{company.name}</BreadcrumbItem>
      </Breadcrumb>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Enterprise size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">
            {company.name}
          </h1>
          <Tag type={company.isActive ? 'green' : 'red'} size="sm">
            {company.isActive ? 'Active' : 'Inactive'}
          </Tag>
        </div>
        <div className="flex gap-2">
          <Button
            kind="primary"
            size="sm"
            renderIcon={Save}
            onClick={handleSave}
            disabled={updateCompany.isPending}
          >
            Save
          </Button>
          {company.isActive && (
            <Button
              kind="danger--ghost"
              size="sm"
              onClick={handleDeactivate}
              disabled={deactivateCompany.isPending}
            >
              Deactivate
            </Button>
          )}
        </div>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Created</p>
          <p className="text-sm font-semibold text-text-primary">
            {formatDate(company.createdAt)}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Sub-Brands</p>
          <p className="text-sm font-semibold text-text-primary">
            {subBrands?.length ?? company.subBrandCount ?? 0}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Stripe Customer</p>
          <p className="text-sm font-semibold text-text-primary">
            {company.stripeCustomerId ?? 'Not connected'}
          </p>
        </Tile>
      </div>

      {/* Edit Details */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Company Details
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextInput
            id="company-name"
            labelText="Company Name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
          />
          <TextInput
            id="contact-email"
            labelText="Contact Email"
            value={editEmail}
            onChange={(e) => setEditEmail(e.target.value)}
          />
          <TextInput
            id="contact-phone"
            labelText="Contact Phone"
            value={editPhone}
            onChange={(e) => setEditPhone(e.target.value)}
          />
        </div>
      </Tile>

      {/* Sub-Brands List */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Sub-Brands
        </h2>
        {!subBrands || subBrands.length === 0 ? (
          <p className="text-sm text-text-secondary">No sub-brands found.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {subBrands.map((sb) => (
              <div
                key={sb.id}
                className="flex items-center justify-between py-2 border-b border-border-subtle-01 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {sb.name}
                  </p>
                  <p className="text-xs text-text-secondary">
                    Slug: {sb.slug}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {sb.isDefault && (
                    <Tag type="blue" size="sm">Default</Tag>
                  )}
                  <Tag type={sb.isActive ? 'green' : 'red'} size="sm">
                    {sb.isActive ? 'Active' : 'Inactive'}
                  </Tag>
                </div>
              </div>
            ))}
          </div>
        )}
      </Tile>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <ToastNotification
            kind={toast.kind}
            title={toast.message}
            timeout={3000}
            onCloseButtonClick={() => setToast(null)}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </div>
  );
}
