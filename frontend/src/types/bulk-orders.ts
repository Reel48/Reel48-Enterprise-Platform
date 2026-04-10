export type BulkOrderStatus =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'cancelled';

export interface BulkOrderLineItem {
  id: string;
  bulkOrderId: string;
  employeeId: string | null;
  productId: string;
  productName: string;
  productSku: string;
  unitPrice: number;
  quantity: number;
  size: string | null;
  decoration: string | null;
  lineTotal: number;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BulkOrder {
  id: string;
  companyId: string;
  subBrandId: string | null;
  catalogId: string;
  createdBy: string;
  title: string;
  description: string | null;
  orderNumber: string;
  status: BulkOrderStatus;
  totalItems: number;
  totalAmount: number;
  submittedAt: string | null;
  approvedBy: string | null;
  approvedAt: string | null;
  cancelledAt: string | null;
  cancelledBy: string | null;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BulkOrderWithItems extends BulkOrder {
  items: BulkOrderLineItem[];
}
