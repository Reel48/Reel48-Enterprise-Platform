import { http, HttpResponse } from 'msw';

const BASE_URL = 'http://localhost:8000';

// --- Mock data for client analytics endpoints ---

export const mockSpendSummary = {
  data: {
    total_spend: 25000.0,
    order_count: 150,
    average_order_value: 166.67,
    individual_order_spend: 15000.0,
    bulk_order_spend: 10000.0,
  },
  meta: {},
  errors: [],
};

export const mockSpendBySubBrand = {
  data: [
    {
      sub_brand_id: 'sb-001',
      sub_brand_name: 'North Division',
      total_spend: 15000.0,
      order_count: 80,
    },
    {
      sub_brand_id: 'sb-002',
      sub_brand_name: 'South Division',
      total_spend: 10000.0,
      order_count: 70,
    },
  ],
  meta: {},
  errors: [],
};

export const mockSpendOverTime = {
  data: [
    { period: '2026-01', total_spend: 8000.0, order_count: 50 },
    { period: '2026-02', total_spend: 9000.0, order_count: 55 },
    { period: '2026-03', total_spend: 8000.0, order_count: 45 },
  ],
  meta: {},
  errors: [],
};

export const mockTopProducts = {
  data: [
    {
      product_id: 'prod-001',
      product_name: 'Premium Polo Shirt',
      product_sku: 'SKU-POLO-001',
      total_quantity: 200,
      total_revenue: 5000.0,
    },
    {
      product_id: 'prod-002',
      product_name: 'Classic T-Shirt',
      product_sku: 'SKU-TEE-002',
      total_quantity: 150,
      total_revenue: 3000.0,
    },
    {
      product_id: 'prod-003',
      product_name: 'Fleece Jacket',
      product_sku: 'SKU-JKT-003',
      total_quantity: 80,
      total_revenue: 4000.0,
    },
  ],
  meta: {},
  errors: [],
};

export const mockOrderStatusBreakdown = {
  data: [
    { status: 'completed', count: 100, order_type: 'individual' },
    { status: 'pending', count: 30, order_type: 'individual' },
    { status: 'completed', count: 15, order_type: 'bulk' },
    { status: 'pending', count: 5, order_type: 'bulk' },
  ],
  meta: {},
  errors: [],
};

export const mockSizeDistribution = {
  data: [
    { size: 'S', count: 20, percentage: 13.33 },
    { size: 'M', count: 50, percentage: 33.33 },
    { size: 'L', count: 45, percentage: 30.0 },
    { size: 'XL', count: 35, percentage: 23.33 },
  ],
  meta: {},
  errors: [],
};

export const mockInvoiceSummary = {
  data: {
    total_invoiced: 30000.0,
    total_paid: 25000.0,
    total_outstanding: 5000.0,
    invoice_count: 12,
    by_status: [
      { status: 'paid', count: 10, total: 25000.0 },
      { status: 'sent', count: 2, total: 5000.0 },
    ],
    by_billing_flow: [
      { billing_flow: 'self_service', count: 8, total: 20000.0 },
      { billing_flow: 'assigned', count: 4, total: 10000.0 },
    ],
  },
  meta: {},
  errors: [],
};

export const mockApprovalMetrics = {
  data: {
    pending_count: 5,
    approved_count: 120,
    rejected_count: 10,
    approval_rate: 92.3,
    avg_approval_time_hours: 4.5,
  },
  meta: {},
  errors: [],
};

// --- Mock data for platform analytics endpoints ---

export const mockPlatformOverview = {
  data: {
    total_companies: 15,
    total_sub_brands: 42,
    total_users: 3500,
    total_orders: 12000,
    total_revenue: 450000.0,
    active_catalogs: 28,
  },
  meta: {},
  errors: [],
};

export const mockRevenueByCompany = {
  data: [
    {
      company_id: 'comp-001',
      company_name: 'Acme Corp',
      total_revenue: 150000.0,
      invoice_count: 25,
    },
    {
      company_id: 'comp-002',
      company_name: 'Global Industries',
      total_revenue: 120000.0,
      invoice_count: 20,
    },
    {
      company_id: 'comp-003',
      company_name: 'Tech Solutions',
      total_revenue: 80000.0,
      invoice_count: 15,
    },
  ],
  meta: {},
  errors: [],
};

// --- MSW Handlers ---

export const analyticsHandlers = [
  // Client analytics endpoints
  http.get(`${BASE_URL}/api/v1/analytics/spend/summary`, () => {
    return HttpResponse.json(mockSpendSummary);
  }),
  http.get(`${BASE_URL}/api/v1/analytics/spend/by-sub-brand`, () => {
    return HttpResponse.json(mockSpendBySubBrand);
  }),
  http.get(`${BASE_URL}/api/v1/analytics/spend/over-time`, () => {
    return HttpResponse.json(mockSpendOverTime);
  }),
  http.get(`${BASE_URL}/api/v1/analytics/orders/top-products`, () => {
    return HttpResponse.json(mockTopProducts);
  }),
  http.get(`${BASE_URL}/api/v1/analytics/orders/status-breakdown`, () => {
    return HttpResponse.json(mockOrderStatusBreakdown);
  }),
  http.get(`${BASE_URL}/api/v1/analytics/orders/size-distribution`, () => {
    return HttpResponse.json(mockSizeDistribution);
  }),
  http.get(`${BASE_URL}/api/v1/analytics/invoices/summary`, () => {
    return HttpResponse.json(mockInvoiceSummary);
  }),
  http.get(`${BASE_URL}/api/v1/analytics/approvals/metrics`, () => {
    return HttpResponse.json(mockApprovalMetrics);
  }),

  // Platform analytics endpoints
  http.get(`${BASE_URL}/api/v1/platform/analytics/overview`, () => {
    return HttpResponse.json(mockPlatformOverview);
  }),
  http.get(`${BASE_URL}/api/v1/platform/analytics/revenue/by-company`, () => {
    return HttpResponse.json(mockRevenueByCompany);
  }),
  http.get(`${BASE_URL}/api/v1/platform/analytics/revenue/over-time`, () => {
    return HttpResponse.json(mockSpendOverTime);
  }),
  http.get(`${BASE_URL}/api/v1/platform/analytics/orders/status-breakdown`, () => {
    return HttpResponse.json(mockOrderStatusBreakdown);
  }),
  http.get(`${BASE_URL}/api/v1/platform/analytics/orders/top-products`, () => {
    return HttpResponse.json(mockTopProducts);
  }),
  http.get(`${BASE_URL}/api/v1/platform/analytics/invoices/summary`, () => {
    return HttpResponse.json(mockInvoiceSummary);
  }),
  http.get(`${BASE_URL}/api/v1/platform/analytics/approvals/metrics`, () => {
    return HttpResponse.json(mockApprovalMetrics);
  }),
];
