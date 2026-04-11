'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  DataTable,
  InlineNotification,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Tag,
  TextInput,
  Tile,
  ToastNotification,
} from '@carbon/react';
import { Enterprise, Save, Copy } from '@carbon/react/icons';

import { StatusTag } from '@/components/ui/StatusTag';
import {
  useCompany,
  useUpdateCompany,
  useDeactivateCompany,
  useReactivateCompany,
  useCompanyCounts,
  useCompanySubBrands,
  useCompanyOrgCode,
  useCompanyUsers,
  useCompanyCatalogs,
  useCompanyOrders,
  useCompanyInvoices,
} from './_hooks';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatPrice(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function catalogStatusColor(status: string): 'green' | 'blue' | 'purple' | 'gray' | 'red' | 'teal' {
  switch (status) {
    case 'active': return 'green';
    case 'approved': return 'teal';
    case 'submitted': return 'blue';
    case 'draft': return 'gray';
    case 'closed': return 'purple';
    case 'archived': return 'red';
    default: return 'gray';
  }
}

function orderStatusColor(status: string): 'green' | 'blue' | 'purple' | 'gray' | 'red' | 'teal' {
  switch (status) {
    case 'delivered': return 'green';
    case 'shipped': return 'teal';
    case 'processing': return 'blue';
    case 'approved': return 'purple';
    case 'pending': return 'gray';
    case 'cancelled': return 'red';
    default: return 'gray';
  }
}

function invoiceStatusColor(status: string): 'green' | 'blue' | 'purple' | 'gray' | 'red' | 'teal' {
  switch (status) {
    case 'paid': return 'green';
    case 'sent': return 'blue';
    case 'finalized': return 'teal';
    case 'draft': return 'gray';
    case 'payment_failed': return 'red';
    case 'voided': return 'red';
    default: return 'gray';
  }
}

function roleColor(role: string): 'green' | 'blue' | 'purple' | 'gray' | 'red' | 'teal' {
  switch (role) {
    case 'corporate_admin': return 'purple';
    case 'sub_brand_admin': return 'blue';
    case 'regional_manager': return 'teal';
    case 'employee': return 'gray';
    default: return 'gray';
  }
}

function formatRole(role: string): string {
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const companyId = params.id;

  // Core data
  const { data: company, isLoading, isError } = useCompany(companyId);
  const updateCompany = useUpdateCompany();
  const deactivateCompany = useDeactivateCompany();
  const reactivateCompany = useReactivateCompany();

  // Summary counts
  const { data: counts } = useCompanyCounts(companyId);

  // Tab state — lazy-load data per tab
  const [activeTab, setActiveTab] = useState(0);

  const { data: subBrandsData } = useCompanySubBrands(companyId);
  const { data: orgCode } = useCompanyOrgCode(companyId);
  const { data: usersData } = useCompanyUsers(companyId, activeTab === 2);
  const { data: catalogsData } = useCompanyCatalogs(companyId, activeTab === 3);
  const { data: ordersData } = useCompanyOrders(companyId, activeTab === 4);
  const { data: invoicesData } = useCompanyInvoices(companyId, activeTab === 5);

  // Edit state
  const [editName, setEditName] = useState('');
  const [initialized, setInitialized] = useState(false);
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [codeCopied, setCodeCopied] = useState(false);

  if (company && !initialized) {
    setEditName(company.name);
    setInitialized(true);
  }

  if (isLoading) {
    return (
      <div className="py-12 text-center text-text-secondary">
        Loading company...
      </div>
    );
  }

  if (isError || !company) {
    return (
      <InlineNotification
        kind="error"
        title="Failed to load company"
        subtitle="The company may not exist."
        hideCloseButton
      />
    );
  }

  const showToast = (kind: 'success' | 'error', message: string) => {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSave = () => {
    updateCompany.mutate(
      { id: companyId, data: { name: editName } },
      {
        onSuccess: () => showToast('success', 'Company updated'),
        onError: () => showToast('error', 'Failed to update company'),
      },
    );
  };

  const handleDeactivate = () => {
    deactivateCompany.mutate(companyId, {
      onSuccess: () => showToast('success', 'Company deactivated'),
    });
  };

  const handleReactivate = () => {
    reactivateCompany.mutate(companyId, {
      onSuccess: () => showToast('success', 'Company reactivated'),
    });
  };

  const handleCopyOrgCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCodeCopied(true);
    setTimeout(() => setCodeCopied(false), 2000);
  };

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb noTrailingSlash>
        <BreadcrumbItem href="/platform/companies">Companies</BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>{company.name}</BreadcrumbItem>
      </Breadcrumb>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Enterprise size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">
            {company.name}
          </h1>
          <StatusTag type={company.isActive ? 'green' : 'red'}>
            {company.isActive ? 'Active' : 'Inactive'}
          </StatusTag>
        </div>
        <div className="flex gap-2">
          <Button
            kind="primary"
            size="sm"
            renderIcon={Save}
            onClick={handleSave}
            disabled={updateCompany.isPending}
          >
            Save
          </Button>
          {company.isActive ? (
            <Button
              kind="danger--ghost"
              size="sm"
              onClick={handleDeactivate}
              disabled={deactivateCompany.isPending}
            >
              Deactivate
            </Button>
          ) : (
            <Button
              kind="ghost"
              size="sm"
              onClick={handleReactivate}
              disabled={reactivateCompany.isPending}
            >
              Reactivate
            </Button>
          )}
        </div>
      </div>

      {/* Summary Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Sub-Brands</p>
          <p className="text-lg font-semibold text-text-primary">
            {counts?.subBrands ?? '—'}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Users</p>
          <p className="text-lg font-semibold text-text-primary">
            {counts?.users ?? '—'}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Catalogs</p>
          <p className="text-lg font-semibold text-text-primary">
            {counts?.catalogs ?? '—'}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Orders</p>
          <p className="text-lg font-semibold text-text-primary">
            {counts?.orders ?? '—'}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Invoices</p>
          <p className="text-lg font-semibold text-text-primary">
            {counts?.invoices ?? '—'}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Created</p>
          <p className="text-sm font-semibold text-text-primary">
            {formatDate(company.createdAt)}
          </p>
        </Tile>
      </div>

      {/* Tabs */}
      <Tabs selectedIndex={activeTab} onChange={({ selectedIndex }) => setActiveTab(selectedIndex)}>
        <TabList aria-label="Company sections">
          <Tab>Overview</Tab>
          <Tab>Sub-Brands</Tab>
          <Tab>Users</Tab>
          <Tab>Catalogs</Tab>
          <Tab>Orders</Tab>
          <Tab>Invoices</Tab>
        </TabList>
        <TabPanels>
          {/* Tab 1: Overview */}
          <TabPanel>
            <div className="flex flex-col gap-6 pt-4">
              {/* Company Details */}
              <Tile>
                <h2 className="text-base font-semibold text-text-primary mb-4">
                  Company Details
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <TextInput
                    id="company-name"
                    labelText="Company Name"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                  <TextInput
                    id="company-slug"
                    labelText="Slug"
                    value={company.slug}
                    readOnly
                    disabled
                  />
                </div>
              </Tile>

              {/* Org Code */}
              <Tile>
                <h2 className="text-base font-semibold text-text-primary mb-4">
                  Organization Code
                </h2>
                {orgCode ? (
                  <div className="flex items-center gap-3">
                    <code className="rounded bg-layer-02 px-3 py-2 text-sm font-mono font-semibold text-text-primary tracking-widest">
                      {orgCode.code}
                    </code>
                    <Button
                      kind="ghost"
                      size="sm"
                      renderIcon={Copy}
                      iconDescription="Copy code"
                      hasIconOnly
                      onClick={() => handleCopyOrgCode(orgCode.code)}
                    />
                    {codeCopied && (
                      <span className="text-xs text-support-success">Copied!</span>
                    )}
                    <StatusTag type={orgCode.isActive ? 'green' : 'red'}>
                      {orgCode.isActive ? 'Active' : 'Inactive'}
                    </StatusTag>
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary">
                    No active organization code.
                  </p>
                )}
              </Tile>
            </div>
          </TabPanel>

          {/* Tab 2: Sub-Brands */}
          <TabPanel>
            <div className="pt-4">
              <Tile>
                <h2 className="text-base font-semibold text-text-primary mb-4">
                  Sub-Brands
                </h2>
                {!subBrandsData || subBrandsData.data.length === 0 ? (
                  <p className="text-sm text-text-secondary">No sub-brands found.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {subBrandsData.data.map((sb) => (
                      <div
                        key={sb.id}
                        className="flex items-center justify-between py-2 border-b border-border-subtle-01 last:border-0"
                      >
                        <div>
                          <p className="text-sm font-medium text-text-primary">
                            {sb.name}
                          </p>
                          <p className="text-xs text-text-secondary">
                            Slug: {sb.slug}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {sb.isDefault && (
                            <StatusTag type="blue">Default</StatusTag>
                          )}
                          <StatusTag type={sb.isActive ? 'green' : 'red'}>
                            {sb.isActive ? 'Active' : 'Inactive'}
                          </StatusTag>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Tile>
            </div>
          </TabPanel>

          {/* Tab 3: Users */}
          <TabPanel>
            <div className="pt-4">
              {!usersData ? (
                <p className="text-sm text-text-secondary py-4">Loading users...</p>
              ) : usersData.data.length === 0 ? (
                <p className="text-sm text-text-secondary py-4">No users found.</p>
              ) : (
                <>
                  <DataTable
                    rows={usersData.data.map((u) => ({
                      id: u.id,
                      fullName: u.fullName,
                      email: u.email,
                      role: u.role,
                      status: u.isActive,
                    }))}
                    headers={[
                      { key: 'fullName', header: 'Full Name' },
                      { key: 'email', header: 'Email' },
                      { key: 'role', header: 'Role' },
                      { key: 'status', header: 'Status' },
                    ]}
                  >
                    {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
                      <TableContainer>
                        <Table {...getTableProps()} size="md">
                          <TableHead>
                            <TableRow>
                              {headers.map((header) => {
                                const { key, ...headerProps } = getHeaderProps({ header, isSortable: false });
                                return (
                                  <TableHeader key={String(key)} {...headerProps}>
                                    {header.header}
                                  </TableHeader>
                                );
                              })}
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {rows.map((row) => {
                              const { key: rowKey, ...rowProps } = getRowProps({ row });
                              const user = usersData.data.find((u) => u.id === row.id);
                              return (
                                <TableRow key={String(rowKey)} {...rowProps}>
                                  <TableCell>{user?.fullName}</TableCell>
                                  <TableCell>{user?.email}</TableCell>
                                  <TableCell>
                                    <Tag type={roleColor(user?.role ?? '')} size="sm">
                                      {formatRole(user?.role ?? '')}
                                    </Tag>
                                  </TableCell>
                                  <TableCell>
                                    <StatusTag type={user?.isActive ? 'green' : 'red'}>
                                      {user?.isActive ? 'Active' : 'Inactive'}
                                    </StatusTag>
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  </DataTable>
                  {usersData.total > 5 && (
                    <p className="text-sm text-link-primary mt-3">
                      Showing 5 of {usersData.total} users
                    </p>
                  )}
                </>
              )}
            </div>
          </TabPanel>

          {/* Tab 4: Catalogs */}
          <TabPanel>
            <div className="pt-4">
              {!catalogsData ? (
                <p className="text-sm text-text-secondary py-4">Loading catalogs...</p>
              ) : catalogsData.data.length === 0 ? (
                <p className="text-sm text-text-secondary py-4">No catalogs found.</p>
              ) : (
                <>
                  <DataTable
                    rows={catalogsData.data.map((c) => ({
                      id: c.id,
                      name: c.name,
                      status: c.status,
                      paymentModel: c.paymentModel,
                      createdAt: c.createdAt,
                    }))}
                    headers={[
                      { key: 'name', header: 'Name' },
                      { key: 'status', header: 'Status' },
                      { key: 'paymentModel', header: 'Payment Model' },
                      { key: 'createdAt', header: 'Created' },
                    ]}
                  >
                    {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
                      <TableContainer>
                        <Table {...getTableProps()} size="md">
                          <TableHead>
                            <TableRow>
                              {headers.map((header) => {
                                const { key, ...headerProps } = getHeaderProps({ header, isSortable: false });
                                return (
                                  <TableHeader key={String(key)} {...headerProps}>
                                    {header.header}
                                  </TableHeader>
                                );
                              })}
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {rows.map((row) => {
                              const { key: rowKey, ...rowProps } = getRowProps({ row });
                              const catalog = catalogsData.data.find((c) => c.id === row.id);
                              return (
                                <TableRow key={String(rowKey)} {...rowProps}>
                                  <TableCell>{catalog?.name}</TableCell>
                                  <TableCell>
                                    <StatusTag type={catalogStatusColor(catalog?.status ?? '')}>
                                      {catalog?.status}
                                    </StatusTag>
                                  </TableCell>
                                  <TableCell>
                                    {catalog?.paymentModel === 'self_service'
                                      ? 'Self Service'
                                      : 'Invoice After Close'}
                                  </TableCell>
                                  <TableCell>
                                    {catalog?.createdAt ? formatDate(catalog.createdAt) : '—'}
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  </DataTable>
                  {catalogsData.total > 5 && (
                    <p className="text-sm mt-3">
                      <a href={`/platform/catalogs?company_id=${companyId}`} className="text-link-primary">
                        View all {catalogsData.total} catalogs
                      </a>
                    </p>
                  )}
                </>
              )}
            </div>
          </TabPanel>

          {/* Tab 5: Orders */}
          <TabPanel>
            <div className="pt-4">
              {!ordersData ? (
                <p className="text-sm text-text-secondary py-4">Loading orders...</p>
              ) : ordersData.data.length === 0 ? (
                <p className="text-sm text-text-secondary py-4">No orders found.</p>
              ) : (
                <>
                  <DataTable
                    rows={ordersData.data.map((o) => ({
                      id: o.id,
                      orderNumber: o.orderNumber,
                      status: o.status,
                      totalAmount: o.totalAmount,
                      createdAt: o.createdAt,
                    }))}
                    headers={[
                      { key: 'orderNumber', header: 'Order #' },
                      { key: 'status', header: 'Status' },
                      { key: 'totalAmount', header: 'Total' },
                      { key: 'createdAt', header: 'Created' },
                    ]}
                  >
                    {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
                      <TableContainer>
                        <Table {...getTableProps()} size="md">
                          <TableHead>
                            <TableRow>
                              {headers.map((header) => {
                                const { key, ...headerProps } = getHeaderProps({ header, isSortable: false });
                                return (
                                  <TableHeader key={String(key)} {...headerProps}>
                                    {header.header}
                                  </TableHeader>
                                );
                              })}
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {rows.map((row) => {
                              const { key: rowKey, ...rowProps } = getRowProps({ row });
                              const order = ordersData.data.find((o) => o.id === row.id);
                              return (
                                <TableRow key={String(rowKey)} {...rowProps}>
                                  <TableCell>{order?.orderNumber}</TableCell>
                                  <TableCell>
                                    <StatusTag type={orderStatusColor(order?.status ?? '')}>
                                      {order?.status}
                                    </StatusTag>
                                  </TableCell>
                                  <TableCell>
                                    {order?.totalAmount != null ? formatPrice(order.totalAmount) : '—'}
                                  </TableCell>
                                  <TableCell>
                                    {order?.createdAt ? formatDate(order.createdAt) : '—'}
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  </DataTable>
                  {ordersData.total > 5 && (
                    <p className="text-sm text-link-primary mt-3">
                      Showing 5 of {ordersData.total} orders
                    </p>
                  )}
                </>
              )}
            </div>
          </TabPanel>

          {/* Tab 6: Invoices */}
          <TabPanel>
            <div className="pt-4">
              {!invoicesData ? (
                <p className="text-sm text-text-secondary py-4">Loading invoices...</p>
              ) : invoicesData.data.length === 0 ? (
                <p className="text-sm text-text-secondary py-4">No invoices found.</p>
              ) : (
                <>
                  <DataTable
                    rows={invoicesData.data.map((inv) => ({
                      id: inv.id,
                      invoiceNumber: inv.invoiceNumber,
                      status: inv.status,
                      billingFlow: inv.billingFlow,
                      totalAmount: inv.totalAmount,
                      createdAt: inv.createdAt,
                    }))}
                    headers={[
                      { key: 'invoiceNumber', header: 'Invoice #' },
                      { key: 'status', header: 'Status' },
                      { key: 'billingFlow', header: 'Billing Flow' },
                      { key: 'totalAmount', header: 'Amount' },
                      { key: 'createdAt', header: 'Created' },
                    ]}
                  >
                    {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
                      <TableContainer>
                        <Table {...getTableProps()} size="md">
                          <TableHead>
                            <TableRow>
                              {headers.map((header) => {
                                const { key, ...headerProps } = getHeaderProps({ header, isSortable: false });
                                return (
                                  <TableHeader key={String(key)} {...headerProps}>
                                    {header.header}
                                  </TableHeader>
                                );
                              })}
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {rows.map((row) => {
                              const { key: rowKey, ...rowProps } = getRowProps({ row });
                              const inv = invoicesData.data.find((i) => i.id === row.id);
                              return (
                                <TableRow key={String(rowKey)} {...rowProps}>
                                  <TableCell>{inv?.invoiceNumber ?? '—'}</TableCell>
                                  <TableCell>
                                    <StatusTag type={invoiceStatusColor(inv?.status ?? '')}>
                                      {inv?.status}
                                    </StatusTag>
                                  </TableCell>
                                  <TableCell>
                                    {inv?.billingFlow === 'self_service'
                                      ? 'Self Service'
                                      : inv?.billingFlow === 'post_window'
                                        ? 'Post Window'
                                        : 'Assigned'}
                                  </TableCell>
                                  <TableCell>
                                    {inv?.totalAmount != null ? formatPrice(inv.totalAmount) : '—'}
                                  </TableCell>
                                  <TableCell>
                                    {inv?.createdAt ? formatDate(inv.createdAt) : '—'}
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  </DataTable>
                  {invoicesData.total > 5 && (
                    <p className="text-sm text-link-primary mt-3">
                      Showing 5 of {invoicesData.total} invoices
                    </p>
                  )}
                </>
              )}
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <ToastNotification
            kind={toast.kind}
            title={toast.message}
            timeout={3000}
            onCloseButtonClick={() => setToast(null)}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </div>
  );
}
