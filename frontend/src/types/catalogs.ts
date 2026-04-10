export type CatalogStatus =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'active'
  | 'closed'
  | 'archived';

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
  companyId: string;
  subBrandId: string | null;
  name: string;
  description: string | null;
  slug: string;
  paymentModel: PaymentModel;
  status: CatalogStatus;
  buyingWindowOpensAt: string | null;
  buyingWindowClosesAt: string | null;
  approvedBy: string | null;
  approvedAt: string | null;
  createdBy: string;
  deletedAt: string | null;
  createdAt: string;
  updatedAt: string;
}
