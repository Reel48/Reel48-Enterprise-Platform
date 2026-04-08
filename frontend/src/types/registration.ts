export interface SubBrandSummary {
  id: string;
  name: string;
  slug: string;
  isDefault: boolean;
}

export interface ValidateOrgCodeData {
  companyName: string;
  subBrands: SubBrandSummary[];
}

export interface RegisterData {
  message: string;
}
