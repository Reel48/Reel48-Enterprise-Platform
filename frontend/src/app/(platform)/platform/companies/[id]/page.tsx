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
  useCompanyOrgCode,
  useCompanyUsers,
} from './_hooks';

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function roleColor(role: string): 'green' | 'blue' | 'purple' | 'gray' | 'red' | 'teal' {
  switch (role) {
    case 'company_admin': return 'purple';
    case 'manager': return 'blue';
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

export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const companyId = params.id;

  const { data: company, isLoading, isError } = useCompany(companyId);
  const updateCompany = useUpdateCompany();
  const deactivateCompany = useDeactivateCompany();
  const reactivateCompany = useReactivateCompany();

  const [activeTab, setActiveTab] = useState(0);

  const { data: orgCode } = useCompanyOrgCode(companyId);
  const { data: usersData } = useCompanyUsers(companyId, activeTab === 1);

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

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Users</p>
          <p className="text-lg font-semibold text-text-primary">
            {usersData?.total ?? '—'}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Slug</p>
          <p className="text-lg font-semibold text-text-primary">
            {company.slug}
          </p>
        </Tile>
        <Tile>
          <p className="text-xs text-text-secondary mb-1">Created</p>
          <p className="text-sm font-semibold text-text-primary">
            {formatDate(company.createdAt)}
          </p>
        </Tile>
      </div>

      <Tabs selectedIndex={activeTab} onChange={({ selectedIndex }) => setActiveTab(selectedIndex)}>
        <TabList aria-label="Company sections">
          <Tab>Overview</Tab>
          <Tab>Users</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            <div className="flex flex-col gap-6 pt-4">
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

          <TabPanel>
            <div className="pt-4">
              {!usersData ? (
                <p className="text-sm text-text-secondary py-4">Loading users...</p>
              ) : usersData.data.length === 0 ? (
                <p className="text-sm text-text-secondary py-4">No users found.</p>
              ) : (
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
              )}
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>

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
