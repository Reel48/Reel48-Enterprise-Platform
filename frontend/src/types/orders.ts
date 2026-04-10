export type OrderStatus =
  | 'pending'
  | 'approved'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'cancelled';

export interface OrderLineItem {
  id: string;
  orderId: string;
  productId: string;
  productName: string;
  productSku: string;
  unitPrice: number;
  quantity: number;
  size: string | null;
  decoration: string | null;
  lineTotal: number;
  createdAt: string;
  updatedAt: string;
}

export interface Order {
  id: string;
  companyId: string;
  subBrandId: string | null;
  userId: string;
  catalogId: string;
  orderNumber: string;
  status: OrderStatus;
  shippingAddressLine1: string | null;
  shippingAddressLine2: string | null;
  shippingCity: string | null;
  shippingState: string | null;
  shippingZip: string | null;
  shippingCountry: string | null;
  notes: string | null;
  subtotal: number;
  totalAmount: number;
  cancelledAt: string | null;
  cancelledBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface OrderWithItems extends Order {
  lineItems: OrderLineItem[];
}
