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

export interface CatalogCreate {
  name: string;
  description?: string;
  paymentModel: PaymentModel;
  buyingWindowOpensAt?: string;
  buyingWindowClosesAt?: string;
}

export interface PlatformCatalogCreate {
  companyId: string;
  subBrandId?: string;
  name: string;
  description?: string;
  paymentModel: PaymentModel;
  buyingWindowOpensAt?: string;
  buyingWindowClosesAt?: string;
}

export interface CatalogUpdate {
  name?: string;
  description?: string;
  buyingWindowOpensAt?: string;
  buyingWindowClosesAt?: string;
}

export interface CatalogProductDetail {
  id: string;
  name: string;
  description: string | null;
  sku: string;
  unitPrice: number;
  sizes: string[];
  decorationOptions: string[];
  imageUrls: string[];
  status: string;
}

export interface CatalogProductEntry {
  id: string;
  catalogId: string;
  productId: string;
  displayOrder: number;
  priceOverride: number | null;
  companyId: string;
  subBrandId: string | null;
  createdAt: string;
  updatedAt: string;
  product?: CatalogProductDetail;
}

export interface CatalogProductAdd {
  productId: string;
  displayOrder?: number;
  priceOverride?: number;
}
