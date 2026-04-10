export interface Company {
  id: string;
  name: string;
  contactEmail: string | null;
  contactPhone: string | null;
  isActive: boolean;
  subBrandCount?: number;
  stripeCustomerId: string | null;
  createdAt: string;
  updatedAt: string;
}
