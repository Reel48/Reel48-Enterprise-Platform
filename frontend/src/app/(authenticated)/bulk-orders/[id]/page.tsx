'use client';

import { useParams } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  InlineNotification,
  Tag,
  Tile,
} from '@carbon/react';
import { GroupResource } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { BulkOrder } from '@/types/bulk-orders';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function statusColor(status: string): 'teal' | 'blue' | 'purple' | 'gray' | 'green' | 'red' {
  switch (status) {
    case 'delivered': return 'green';
    case 'shipped': case 'processing': return 'blue';
    case 'approved': return 'teal';
    case 'pending': case 'submitted': case 'draft': return 'purple';
    case 'cancelled': return 'red';
    default: return 'gray';
  }
}

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useBulkOrder(id: string) {
  return useQuery({
    queryKey: ['bulk-order', id],
    queryFn: async () => {
      const res = await api.get<BulkOrder>(`/api/v1/bulk_orders/${id}`);
      return res.data;
    },
  });
}

function useBulkOrderAction(action: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/bulk_orders/${id}/${action}`);
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['bulk-order', id] });
      queryClient.invalidateQueries({ queryKey: ['bulk-orders'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BulkOrderDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: bulkOrder, isLoading, isError } = useBulkOrder(params.id);
  const submitAction = useBulkOrderAction('submit');
  const approveAction = useBulkOrderAction('approve');
  const cancelAction = useBulkOrderAction('cancel');

  if (isLoading) {
    return (
      <div className="py-12 text-center text-text-secondary">
        Loading bulk order...
      </div>
    );
  }

  if (isError || !bulkOrder) {
    return (
      <InlineNotification
        kind="error"
        title="Failed to load bulk order"
        subtitle="The bulk order may not exist or you don't have access."
        hideCloseButton
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/bulk-orders">Bulk Orders</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>
          {bulkOrder.name ?? 'Bulk Order'}
        </BreadcrumbItem>
      </Breadcrumb>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GroupResource size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">
            {bulkOrder.name ?? 'Bulk Order'}
          </h1>
          <Tag type={statusColor(bulkOrder.status)} size="sm">
            {bulkOrder.status}
          </Tag>
        </div>
        <div className="flex gap-2">
          {bulkOrder.status === 'draft' && (
            <Button
              kind="primary"
              size="sm"
              onClick={() => submitAction.mutate(params.id)}
              disabled={submitAction.isPending}
            >
              Submit for Approval
            </Button>
          )}
          {bulkOrder.status === 'submitted' && (
            <Button
              kind="primary"
              size="sm"
              onClick={() => approveAction.mutate(params.id)}
              disabled={approveAction.isPending}
            >
              Approve
            </Button>
          )}
          {(bulkOrder.status === 'draft' || bulkOrder.status === 'submitted') && (
            <Button
              kind="danger--ghost"
              size="sm"
              onClick={() => cancelAction.mutate(params.id)}
              disabled={cancelAction.isPending}
            >
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Total Amount</p>
          <p className="text-xl font-semibold text-text-primary">
            {formatPrice(bulkOrder.totalAmount)}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Items</p>
          <p className="text-xl font-semibold text-text-primary">
            {bulkOrder.itemCount}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Created By</p>
          <p className="text-xl font-semibold text-text-primary">
            {bulkOrder.createdByName ?? '—'}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Created</p>
          <p className="text-xl font-semibold text-text-primary">
            {formatDate(bulkOrder.createdAt)}
          </p>
        </Tile>
      </div>

      {/* Line Items */}
      {bulkOrder.lineItems && bulkOrder.lineItems.length > 0 && (
        <Tile>
          <h2 className="text-base font-semibold text-text-primary mb-4">
            Line Items
          </h2>
          <div className="flex flex-col gap-3">
            {bulkOrder.lineItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between py-2 border-b border-border-subtle-01 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {item.productName}
                  </p>
                  <p className="text-xs text-text-secondary">
                    SKU: {item.productSku}
                    {item.size && ` · Size: ${item.size}`}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-text-primary">
                    {formatPrice(item.totalPrice)}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {item.quantity} × {formatPrice(item.unitPrice)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Tile>
      )}
    </div>
  );
}
