export type ProductStatus =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'active'
  | 'archived';

export interface Product {
  id: string;
  companyId: string;
  subBrandId: string | null;
  name: string;
  description: string | null;
  sku: string;
  unitPrice: number;
  sizes: string[];
  decorationOptions: string[];
  imageUrls: string[];
  status: ProductStatus;
  approvedBy: string | null;
  approvedAt: string | null;
  createdBy: string;
  deletedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProductCreate {
  name: string;
  description?: string;
  sku: string;
  unitPrice: number;
  sizes?: string[];
  decorationOptions?: string[];
}

export interface ProductUpdate {
  name?: string;
  description?: string;
  sku?: string;
  unitPrice?: number;
  sizes?: string[];
  decorationOptions?: string[];
}
