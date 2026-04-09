export interface SpendSummary {
  totalSpend: number;
  orderCount: number;
  averageOrderValue: number;
  individualOrderSpend: number;
  bulkOrderSpend: number;
}

export interface SubBrandSpend {
  subBrandId: string;
  subBrandName: string;
  totalSpend: number;
  orderCount: number;
}

export interface SpendOverTime {
  period: string;
  totalSpend: number;
  orderCount: number;
}

export interface OrderStatusBreakdown {
  status: string;
  count: number;
  orderType: string;
}

export interface TopProduct {
  productId: string;
  productName: string;
  productSku: string;
  totalQuantity: number;
  totalRevenue: number;
}

export interface SizeDistribution {
  size: string;
  count: number;
  percentage: number;
}

export interface InvoiceStatusBreakdown {
  status: string;
  count: number;
  total: number;
}

export interface InvoiceBillingFlowBreakdown {
  billingFlow: string;
  count: number;
  total: number;
}

export interface InvoiceSummary {
  totalInvoiced: number;
  totalPaid: number;
  totalOutstanding: number;
  invoiceCount: number;
  byStatus: InvoiceStatusBreakdown[];
  byBillingFlow: InvoiceBillingFlowBreakdown[];
}

export interface ApprovalMetrics {
  pendingCount: number;
  approvedCount: number;
  rejectedCount: number;
  approvalRate: number;
  avgApprovalTimeHours: number | null;
}

export interface PlatformOverview {
  totalCompanies: number;
  totalSubBrands: number;
  totalUsers: number;
  totalOrders: number;
  totalRevenue: number;
  activeCatalogs: number;
}

export interface CompanyRevenue {
  companyId: string;
  companyName: string;
  totalRevenue: number;
  invoiceCount: number;
}
