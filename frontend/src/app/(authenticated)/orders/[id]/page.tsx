'use client';

import { useParams } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  InlineNotification,
  Tile,
} from '@carbon/react';
import { ShoppingCart } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';
import type { OrderWithItems } from '@/types/orders';

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
    case 'pending': return 'purple';
    case 'cancelled': return 'red';
    default: return 'gray';
  }
}

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useOrder(orderId: string) {
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: async () => {
      const res = await api.get<OrderWithItems>(`/api/v1/orders/${orderId}`);
      return res.data;
    },
  });
}

function useCancelOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      await api.post(`/api/v1/orders/${orderId}/cancel`);
    },
    onSuccess: (_data, orderId) => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: order, isLoading, isError } = useOrder(params.id);
  const cancelOrder = useCancelOrder();

  if (isLoading) {
    return (
      <div className="py-12 text-center text-text-secondary">
        Loading order...
      </div>
    );
  }

  if (isError || !order) {
    return (
      <InlineNotification
        kind="error"
        title="Failed to load order"
        subtitle="The order may not exist or you don't have access."
        hideCloseButton
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/orders">Orders</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>{order.orderNumber}</BreadcrumbItem>
      </Breadcrumb>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShoppingCart size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">
            {order.orderNumber}
          </h1>
          <StatusTag type={statusColor(order.status)}>
            {order.status}
          </StatusTag>
        </div>
        {order.status === 'pending' && (
          <Button
            kind="danger--ghost"
            size="sm"
            onClick={() => cancelOrder.mutate(order.id)}
            disabled={cancelOrder.isPending}
          >
            Cancel Order
          </Button>
        )}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Total Amount</p>
          <p className="text-xl font-semibold text-text-primary">
            {formatPrice(order.totalAmount)}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Items</p>
          <p className="text-xl font-semibold text-text-primary">
            {order.lineItems?.length ?? 0}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Placed</p>
          <p className="text-xl font-semibold text-text-primary">
            {formatDate(order.createdAt)}
          </p>
        </Tile>
      </div>

      {/* Line Items */}
      {order.lineItems && order.lineItems.length > 0 && (
        <Tile>
          <h2 className="text-base font-semibold text-text-primary mb-4">
            Order Items
          </h2>
          <div className="flex flex-col gap-3">
            {order.lineItems.map((item) => (
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
                    {formatPrice(item.lineTotal)}
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
