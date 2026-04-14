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
import { Receipt, DocumentPdf, Launch } from '@carbon/react/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';

import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';
import type { Invoice } from '@/types/invoices';

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
    case 'linked': return 'Linked';
    default: return flow;
  }
}

function statusLabel(status: string): string {
  return status.replace(/_/g, ' ');
}

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useInvoice(invoiceId: string) {
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: async () => {
      const res = await api.get<Invoice>(`/api/v1/invoices/${invoiceId}`);
      return res.data;
    },
  });
}

function useInvoicePdf(invoiceId: string) {
  return useMutation({
    mutationFn: async () => {
      const res = await api.get<{ url: string }>(`/api/v1/invoices/${invoiceId}/pdf`);
      return res.data;
    },
    onSuccess: (data) => {
      if (data?.url) {
        window.open(data.url, '_blank', 'noopener,noreferrer');
      }
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: invoice, isLoading, isError } = useInvoice(params.id);
  const downloadPdf = useInvoicePdf(params.id);

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
        subtitle="The invoice may not exist or you don't have access."
        hideCloseButton
      />
    );
  }

  const displayNumber = invoice.invoiceNumber ?? 'Draft Invoice';

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/invoices">Invoices</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>{displayNumber}</BreadcrumbItem>
      </Breadcrumb>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Receipt size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">
            {displayNumber}
          </h1>
          <StatusTag type={statusColor(invoice.status)}>
            {statusLabel(invoice.status)}
          </StatusTag>
          <Tag type="gray" size="sm">
            {billingFlowLabel(invoice.billingFlow)}
          </Tag>
        </div>
      </div>

      {/* Summary Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Total Amount</p>
          <p className="text-xl font-semibold text-text-primary">
            {formatPrice(invoice.totalAmount)}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Status</p>
          <div className="mt-1">
            <StatusTag type={statusColor(invoice.status)}>
              {statusLabel(invoice.status)}
            </StatusTag>
          </div>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Billing Flow</p>
          <p className="text-xl font-semibold text-text-primary">
            {billingFlowLabel(invoice.billingFlow)}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Due Date</p>
          <p className="text-xl font-semibold text-text-primary">
            {formatDate(invoice.dueDate)}
          </p>
        </Tile>
      </div>

      {/* Detail Section */}
      <Tile>
        <h2 className="text-base font-semibold text-text-primary mb-4">
          Invoice Details
        </h2>
        <div className="flex flex-col gap-3">
          <DetailRow label="Invoice Number" value={invoice.invoiceNumber ?? '—'} />
          <DetailRow label="Currency" value={invoice.currency.toUpperCase()} />
          <DetailRow label="Created" value={formatDate(invoice.createdAt)} />
          {invoice.paidAt && (
            <DetailRow label="Paid" value={formatDate(invoice.paidAt)} />
          )}
          {invoice.buyingWindowClosesAt && (
            <DetailRow label="Buying Window Closes" value={formatDate(invoice.buyingWindowClosesAt)} />
          )}
          {invoice.orderId && (
            <div className="flex items-center justify-between py-2 border-b border-border-subtle-01 last:border-0">
              <span className="text-sm text-text-secondary">Related Order</span>
              <Link href={`/orders/${invoice.orderId}`} className="text-sm text-link-primary hover:underline">
                View Order
              </Link>
            </div>
          )}
          {invoice.bulkOrderId && (
            <div className="flex items-center justify-between py-2 border-b border-border-subtle-01 last:border-0">
              <span className="text-sm text-text-secondary">Related Bulk Order</span>
              <Link href={`/bulk-orders/${invoice.bulkOrderId}`} className="text-sm text-link-primary hover:underline">
                View Bulk Order
              </Link>
            </div>
          )}
        </div>
      </Tile>

      {/* Action Links */}
      <div className="flex gap-3">
        <Button
          kind="primary"
          size="sm"
          renderIcon={Launch}
          disabled={!invoice.stripeInvoiceUrl}
          onClick={() => {
            if (invoice.stripeInvoiceUrl) {
              window.open(invoice.stripeInvoiceUrl, '_blank', 'noopener,noreferrer');
            }
          }}
        >
          View on Stripe
        </Button>
        <Button
          kind="secondary"
          size="sm"
          renderIcon={DocumentPdf}
          disabled={downloadPdf.isPending || invoice.status === 'draft'}
          onClick={() => downloadPdf.mutate()}
        >
          {downloadPdf.isPending ? 'Loading...' : 'Download PDF'}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border-subtle-01 last:border-0">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm font-medium text-text-primary">{value}</span>
    </div>
  );
}
