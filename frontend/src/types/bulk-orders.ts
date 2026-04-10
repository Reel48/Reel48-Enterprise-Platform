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
  productId: string;
  productName: string;
  productSku: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  size: string | null;
}

export interface BulkOrder {
  id: string;
  name: string | null;
  status: BulkOrderStatus;
  totalAmount: number;
  itemCount: number;
  companyId: string;
  subBrandId: string;
  createdById: string;
  createdByName?: string;
  lineItems?: BulkOrderLineItem[];
  createdAt: string;
  updatedAt: string;
}
