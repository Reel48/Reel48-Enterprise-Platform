export type OrderStatus =
  | 'pending'
  | 'approved'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'cancelled';

export interface OrderLineItem {
  id: string;
  productId: string;
  productName: string;
  productSku: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  size: string | null;
}

export interface Order {
  id: string;
  orderNumber: string;
  status: OrderStatus;
  totalAmount: number;
  itemCount: number;
  userId: string;
  companyId: string;
  subBrandId: string;
  lineItems?: OrderLineItem[];
  createdAt: string;
  updatedAt: string;
}
