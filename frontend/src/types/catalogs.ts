export type CatalogStatus =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'active'
  | 'closed';

export type PaymentModel = 'self_service' | 'invoice_after_close';

export interface CatalogProduct {
  id: string;
  name: string;
  sku: string;
  unitPrice: number;
  imageUrls: string[];
  sizes: string[];
  status: string;
}

export interface Catalog {
  id: string;
  name: string;
  description: string | null;
  status: CatalogStatus;
  paymentModel: PaymentModel;
  companyId: string;
  companyName?: string;
  subBrandId: string | null;
  productCount: number;
  buyingWindowOpensAt: string | null;
  buyingWindowClosesAt: string | null;
  createdAt: string;
  updatedAt: string;
}
