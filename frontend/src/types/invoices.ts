export type InvoiceStatus =
  | 'draft'
  | 'finalized'
  | 'sent'
  | 'paid'
  | 'payment_failed'
  | 'voided';

export type BillingFlow = 'assigned' | 'self_service' | 'post_window' | 'linked';

export interface Invoice {
  id: string;
  companyId: string;
  subBrandId: string | null;
  orderId: string | null;
  bulkOrderId: string | null;
  catalogId: string | null;
  stripeInvoiceId: string;
  stripeInvoiceUrl: string | null;
  stripePdfUrl: string | null;
  invoiceNumber: string | null;
  billingFlow: BillingFlow;
  status: InvoiceStatus;
  totalAmount: number;
  currency: string;
  dueDate: string | null;
  buyingWindowClosesAt: string | null;
  createdBy: string;
  paidAt: string | null;
  createdAt: string;
  updatedAt: string;
}

/** Lighter version used in list views */
export interface InvoiceSummary {
  id: string;
  invoiceNumber: string | null;
  billingFlow: BillingFlow;
  status: InvoiceStatus;
  totalAmount: number;
  currency: string;
  companyId: string;
  subBrandId: string | null;
  createdAt: string;
  paidAt: string | null;
}
