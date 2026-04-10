'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  InlineNotification,
  TextInput,
  Tile,
} from '@carbon/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { BulkOrder } from '@/types/bulk-orders';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NewBulkOrderPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const createBulkOrder = useMutation({
    mutationFn: async (data: { name: string }) => {
      const res = await api.post<BulkOrder>('/api/v1/bulk_orders/', data);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['bulk-orders'] });
      router.push(`/bulk-orders/${data.id}`);
    },
    onError: () => {
      setError('Failed to create bulk order. Please try again.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    createBulkOrder.mutate({ name: name.trim() || 'Untitled Bulk Order' });
  };

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/bulk-orders">Bulk Orders</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>New</BreadcrumbItem>
      </Breadcrumb>

      <h1 className="text-2xl font-semibold text-text-primary">
        Create Bulk Order
      </h1>

      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onCloseButtonClick={() => setError(null)}
        />
      )}

      <Tile>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <TextInput
            id="bulk-order-name"
            labelText="Bulk Order Name"
            placeholder="e.g., Q2 Company Polo Order"
            value={name}
            onChange={(e) => setName(e.target.value)}
            helperText="Give this order a descriptive name so it's easy to find later"
          />
          <div className="flex gap-2 mt-2">
            <Button
              kind="primary"
              type="submit"
              disabled={createBulkOrder.isPending}
            >
              {createBulkOrder.isPending ? 'Creating...' : 'Create Bulk Order'}
            </Button>
            <Button kind="secondary" href="/bulk-orders">
              Cancel
            </Button>
          </div>
        </form>
      </Tile>
    </div>
  );
}
