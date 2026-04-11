'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  InlineNotification,
  Modal,
  Tile,
  ToastNotification,
} from '@carbon/react';
import { ShoppingCart } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/lib/auth/hooks';
import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';
import type { Order, OrderWithItems, OrderStatus } from '@/types/orders';
import type { UserRole } from '@/types/auth';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MANAGER_AND_ABOVE: UserRole[] = [
  'reel48_admin',
  'corporate_admin',
  'sub_brand_admin',
  'regional_manager',
];

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

function useOrderTransition(action: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      const res = await api.post<Order>(`/api/v1/orders/${orderId}/${action}`);
      return res.data;
    },
    onSuccess: (_data, orderId) => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
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
// Action button config per status
// ---------------------------------------------------------------------------

interface ActionConfig {
  label: string;
  action: string;
  needsConfirm: boolean;
  managerOnly: boolean;
}

const STATUS_ACTIONS: Partial<Record<OrderStatus, ActionConfig>> = {
  pending: { label: 'Approve', action: 'approve', needsConfirm: true, managerOnly: true },
  approved: { label: 'Process', action: 'process', needsConfirm: false, managerOnly: true },
  processing: { label: 'Ship', action: 'ship', needsConfirm: false, managerOnly: true },
  shipped: { label: 'Deliver', action: 'deliver', needsConfirm: false, managerOnly: true },
};

function canCancel(status: OrderStatus, isManager: boolean): boolean {
  if (status === 'pending') return true;
  if (status === 'approved' && isManager) return true;
  return false;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const { user } = useAuth();
  const { data: order, isLoading, isError } = useOrder(params.id);

  const role = user?.tenantContext.role ?? 'employee';
  const isManager = MANAGER_AND_ABOVE.includes(role);

  const approveOrder = useOrderTransition('approve');
  const processOrder = useOrderTransition('process');
  const shipOrder = useOrderTransition('ship');
  const deliverOrder = useOrderTransition('deliver');
  const cancelOrder = useCancelOrder();

  const transitionMutations: Record<string, ReturnType<typeof useOrderTransition>> = {
    approve: approveOrder,
    process: processOrder,
    ship: shipOrder,
    deliver: deliverOrder,
  };

  const [confirmModal, setConfirmModal] = useState<'approve' | 'cancel' | null>(null);
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  function showToast(kind: 'success' | 'error', message: string) {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  }

  function handleTransition(action: string) {
    if (!order) return;
    const mutation = transitionMutations[action];
    if (!mutation) return;
    mutation.mutate(order.id, {
      onSuccess: () => showToast('success', `Order ${action}${action.endsWith('e') ? 'd' : 'ed'} successfully`),
      onError: () => showToast('error', `Failed to ${action} order`),
    });
  }

  function handleCancel() {
    if (!order) return;
    cancelOrder.mutate(order.id, {
      onSuccess: () => showToast('success', 'Order cancelled successfully'),
      onError: () => showToast('error', 'Failed to cancel order'),
    });
  }

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

  const primaryAction = STATUS_ACTIONS[order.status];
  const showPrimary = primaryAction && (!primaryAction.managerOnly || isManager);
  const showCancel = canCancel(order.status, isManager);
  const anyMutationPending =
    approveOrder.isPending || processOrder.isPending || shipOrder.isPending ||
    deliverOrder.isPending || cancelOrder.isPending;

  return (
    <div className="flex flex-col gap-6">
      {toast && (
        <ToastNotification
          kind={toast.kind}
          title={toast.kind === 'success' ? 'Success' : 'Error'}
          subtitle={toast.message}
          onClose={() => setToast(null)}
          timeout={3000}
        />
      )}

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
        {(showPrimary || showCancel) && (
          <div className="flex gap-3">
            {showPrimary && (
              <Button
                kind="primary"
                size="sm"
                disabled={anyMutationPending}
                onClick={() => {
                  if (primaryAction.needsConfirm) {
                    setConfirmModal('approve');
                  } else {
                    handleTransition(primaryAction.action);
                  }
                }}
              >
                {primaryAction.label}
              </Button>
            )}
            {showCancel && (
              <Button
                kind="danger--ghost"
                size="sm"
                disabled={anyMutationPending}
                onClick={() => setConfirmModal('cancel')}
              >
                Cancel Order
              </Button>
            )}
          </div>
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

      {/* Approve confirmation modal */}
      <Modal
        open={confirmModal === 'approve'}
        modalHeading="Approve Order"
        primaryButtonText="Approve"
        secondaryButtonText="Go back"
        onRequestClose={() => setConfirmModal(null)}
        onRequestSubmit={() => {
          setConfirmModal(null);
          handleTransition('approve');
        }}
      >
        <p>
          Are you sure you want to approve order <strong>{order.orderNumber}</strong>?
          This will move it to the processing queue.
        </p>
      </Modal>

      {/* Cancel confirmation modal */}
      <Modal
        open={confirmModal === 'cancel'}
        modalHeading="Cancel Order"
        primaryButtonText="Cancel Order"
        primaryButtonDisabled={cancelOrder.isPending}
        secondaryButtonText="Go back"
        danger
        onRequestClose={() => setConfirmModal(null)}
        onRequestSubmit={() => {
          setConfirmModal(null);
          handleCancel();
        }}
      >
        <p>
          Are you sure you want to cancel order <strong>{order.orderNumber}</strong>?
          This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
