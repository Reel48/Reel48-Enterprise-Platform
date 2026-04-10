export type InvoiceStatus =
  | 'draft'
  | 'finalized'
  | 'sent'
  | 'paid'
  | 'payment_failed'
  | 'voided';

export type BillingFlow = 'assigned' | 'self_service' | 'post_window';

export interface Invoice {
  id: string;
  invoiceNumber: string | null;
  companyId: string;
  companyName?: string;
  subBrandId: string | null;
  stripeInvoiceId: string;
  stripeInvoiceUrl: string | null;
  stripePdfUrl: string | null;
  billingFlow: BillingFlow;
  status: InvoiceStatus;
  totalAmount: number;
  currency: string;
  dueDate: string | null;
  paidAt: string | null;
  createdById: string;
  createdAt: string;
  updatedAt: string;
}
