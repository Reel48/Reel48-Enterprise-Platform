'use client';

import { useParams } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  InlineNotification,
  Tag,
  Tile,
  ToastNotification,
} from '@carbon/react';
import { Receipt } from '@carbon/react/icons';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Invoice, InvoiceStatus } from '@/types/invoices';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '—';
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
    case 'paid': return 'green';
    case 'sent': return 'blue';
    case 'finalized': return 'teal';
    case 'draft': return 'purple';
    case 'payment_failed': case 'voided': return 'red';
    default: return 'gray';
  }
}

function billingFlowLabel(flow: string): string {
  switch (flow) {
    case 'assigned': return 'Assigned';
    case 'self_service': return 'Self-Service';
    case 'post_window': return 'Post-Window';
    default: return flow;
  }
}

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useInvoice(id: string) {
  return useQuery({
    queryKey: ['platform-invoice', id],
    queryFn: async () => {
      const res = await api.get<Invoice>(`/api/v1/platform/invoices/${id}`);
      return res.data;
    },
  });
}

function useInvoiceAction(action: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/platform/invoices/${id}/${action}`);
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['platform-invoice', id] });
      queryClient.invalidateQueries({ queryKey: ['platform-invoices'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: invoice, isLoading, isError } = useInvoice(params.id);
  const finalizeAction = useInvoiceAction('finalize');
  const sendAction = useInvoiceAction('send');
  const voidAction = useInvoiceAction('void');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  if (isLoading) {
    return (
      <div className="py-12 text-center text-text-secondary">
        Loading invoice...
      </div>
    );
  }

  if (isError || !invoice) {
    return (
      <InlineNotification
        kind="error"
        title="Failed to load invoice"
        subtitle="The invoice may not exist."
        hideCloseButton
      />
    );
  }

  const getAvailableActions = (status: InvoiceStatus): string[] => {
    switch (status) {
      case 'draft': return ['finalize', 'void'];
      case 'finalized': return ['send', 'void'];
      case 'sent': return ['void'];
      default: return [];
    }
  };

  const actions = getAvailableActions(invoice.status);

  const handleAction = (
    action: ReturnType<typeof useInvoiceAction>,
    label: string,
  ) => {
    action.mutate(params.id, {
      onSuccess: () => {
        setToast({ kind: 'success', message: `Invoice ${label} successfully` });
        setTimeout(() => setToast(null), 3000);
      },
      onError: () => {
        setToast({ kind: 'error', message: `Failed to ${label.toLowerCase()} invoice` });
        setTimeout(() => setToast(null), 3000);
      },
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/platform/invoices">Invoices</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>
          {invoice.invoiceNumber ?? 'Draft'}
        </BreadcrumbItem>
      </Breadcrumb>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Receipt size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">
            {invoice.invoiceNumber ?? 'Draft Invoice'}
          </h1>
          <Tag type={statusColor(invoice.status)} size="sm">
            {invoice.status.replace('_', ' ')}
          </Tag>
          <Tag type="gray" size="sm">
            {billingFlowLabel(invoice.billingFlow)}
          </Tag>
        </div>
        <div className="flex gap-2">
          {actions.includes('finalize') && (
            <Button
              kind="primary"
              size="sm"
              onClick={() => handleAction(finalizeAction, 'finalized')}
              disabled={finalizeAction.isPending}
            >
              Finalize
            </Button>
          )}
          {actions.includes('send') && (
            <Button
              kind="primary"
              size="sm"
              onClick={() => handleAction(sendAction, 'sent')}
              disabled={sendAction.isPending}
            >
              Send
            </Button>
          )}
          {actions.includes('void') && (
            <Button
              kind="danger--ghost"
              size="sm"
              onClick={() => handleAction(voidAction, 'voided')}
              disabled={voidAction.isPending}
            >
              Void
            </Button>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Total Amount</p>
          <p className="text-xl font-semibold text-text-primary">
            {formatPrice(invoice.totalAmount)}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Company</p>
          <p className="text-sm font-semibold text-text-primary">
            {invoice.companyName ?? invoice.companyId}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Due Date</p>
          <p className="text-sm font-semibold text-text-primary">
            {formatDate(invoice.dueDate)}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Created</p>
          <p className="text-sm font-semibold text-text-primary">
            {formatDate(invoice.createdAt)}
          </p>
        </Tile>
      </div>

      {/* Stripe Info */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Stripe Details
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-text-secondary mb-1">Stripe Invoice ID</p>
            <p className="text-sm text-text-primary font-mono">
              {invoice.stripeInvoiceId}
            </p>
          </div>
          {invoice.stripeInvoiceUrl && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Hosted Invoice</p>
              <a
                href={invoice.stripeInvoiceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-link-primary"
              >
                View on Stripe
              </a>
            </div>
          )}
          {invoice.stripePdfUrl && (
            <div>
              <p className="text-xs text-text-secondary mb-1">PDF</p>
              <a
                href={invoice.stripePdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-link-primary"
              >
                Download PDF
              </a>
            </div>
          )}
          {invoice.paidAt && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Paid At</p>
              <p className="text-sm text-text-primary">
                {formatDate(invoice.paidAt)}
              </p>
            </div>
          )}
        </div>
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
