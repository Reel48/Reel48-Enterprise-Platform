export interface Profile {
  id: string;
  companyId: string;
  userId: string;
  department: string | null;
  jobTitle: string | null;
  location: string | null;
  shirtSize: string | null;
  pantSize: string | null;
  shoeSize: string | null;
  deliveryAddressLine1: string | null;
  deliveryAddressLine2: string | null;
  deliveryCity: string | null;
  deliveryState: string | null;
  deliveryZip: string | null;
  deliveryCountry: string | null;
  notes: string | null;
  profilePhotoUrl: string | null;
  onboardingComplete: boolean;
  createdAt: string;
  updatedAt: string;
}

export const SHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL'] as const;

export const PANT_SIZES = [
  '28', '29', '30', '31', '32', '33', '34', '36', '38', '40', '42', '44',
] as const;

export const SHOE_SIZES = [
  '6', '6.5', '7', '7.5', '8', '8.5', '9', '9.5', '10', '10.5',
  '11', '11.5', '12', '13', '14', '15',
] as const;
