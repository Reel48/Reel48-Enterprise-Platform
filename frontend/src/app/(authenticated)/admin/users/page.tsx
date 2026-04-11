'use client';

import { useEffect, useState } from 'react';
import {
  Button,
  DataTable,
  Dropdown,
  InlineNotification,
  Modal,
  Pagination,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  TableToolbar,
  TableToolbarContent,
  Tabs,
  Tag,
  TextInput,
  ToastNotification,
} from '@carbon/react';
import { UserProfile, Add, Copy, TrashCan } from '@carbon/react/icons';

import { useAuth } from '@/lib/auth/hooks';
import { StatusTag } from '@/components/ui/StatusTag';
import type { UserRole } from '@/types/auth';

import type { Invite, SubBrand, User } from './_types';
import {
  useCreateInvite,
  useCurrentOrgCode,
  useDeactivateOrgCode,
  useDeactivateUser,
  useDeleteInvite,
  useGenerateOrgCode,
  useInvites,
  useSubBrands,
  useUsers,
} from './_hooks';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function roleLabel(role: string): string {
  return role.replace(/_/g, ' ');
}

function roleColor(role: string): 'purple' | 'teal' | 'blue' | 'green' | 'gray' {
  switch (role) {
    case 'corporate_admin': return 'purple';
    case 'sub_brand_admin': return 'teal';
    case 'regional_manager': return 'blue';
    case 'employee': return 'green';
    default: return 'gray';
  }
}

function inviteStatus(invite: Invite): 'consumed' | 'expired' | 'pending' {
  if (invite.consumedAt) return 'consumed';
  if (new Date(invite.expiresAt) < new Date()) return 'expired';
  return 'pending';
}

function inviteStatusColor(status: string): 'teal' | 'red' | 'gray' {
  switch (status) {
    case 'pending': return 'teal';
    case 'expired': return 'red';
    case 'consumed': return 'gray';
    default: return 'gray';
  }
}

const ROLE_FILTER_OPTIONS = [
  { id: 'all', text: 'All Roles' },
  { id: 'corporate_admin', text: 'Corporate Admin' },
  { id: 'sub_brand_admin', text: 'Sub-Brand Admin' },
  { id: 'regional_manager', text: 'Regional Manager' },
  { id: 'employee', text: 'Employee' },
];

const INVITE_ROLE_OPTIONS = [
  { id: 'employee', text: 'Employee' },
  { id: 'regional_manager', text: 'Regional Manager' },
  { id: 'sub_brand_admin', text: 'Sub-Brand Admin' },
];

const CAN_MANAGE_USERS: UserRole[] = ['corporate_admin', 'sub_brand_admin'];

// ---------------------------------------------------------------------------
// Users Tab
// ---------------------------------------------------------------------------

function UsersTab({
  canManage,
  onToast,
}: {
  canManage: boolean;
  onToast: (kind: 'success' | 'error', message: string) => void;
}) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [roleFilter, setRoleFilter] = useState('all');

  const { data, isLoading, isError } = useUsers(page, perPage, roleFilter);
  const deactivateUser = useDeactivateUser();

  const users: User[] = data?.data ?? [];
  const total = Number(data?.meta?.total ?? 0);

  const tableHeaders = [
    { key: 'fullName', header: 'Name' },
    { key: 'email', header: 'Email' },
    { key: 'role', header: 'Role' },
    { key: 'subBrandName', header: 'Sub-Brand' },
    { key: 'status', header: 'Status' },
    { key: 'createdAt', header: 'Joined' },
    { key: 'actions', header: '' },
  ];

  const tableRows = users.map((u) => ({
    id: u.id,
    fullName: u.fullName,
    email: u.email,
    role: u.role,
    subBrandName: u.subBrandName ?? '—',
    status: u.isActive,
    createdAt: u.createdAt,
  }));

  const handleDeactivate = (userId: string) => {
    deactivateUser.mutate(userId, {
      onSuccess: () => onToast('success', 'User deactivated'),
      onError: () => onToast('error', 'Failed to deactivate user'),
    });
  };

  return (
    <>
      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load users"
          subtitle="Please try refreshing the page."
          hideCloseButton
        />
      )}

      <DataTable rows={tableRows} headers={tableHeaders} isSortable={false}>
        {({ rows: tableRowsProp, headers, getHeaderProps, getRowProps, getTableProps }) => (
          <TableContainer>
            <TableToolbar>
              <TableToolbarContent>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-medium" style={{ color: 'var(--cds-text-secondary)' }}>Filter:</span>
                  <Dropdown
                    id="role-filter"
                    titleText=""
                    label="All Roles"
                    items={ROLE_FILTER_OPTIONS}
                    itemToString={(item) => item?.text ?? ''}
                    initialSelectedItem={ROLE_FILTER_OPTIONS[0]}
                    onChange={({ selectedItem }) => {
                      setRoleFilter(selectedItem?.id ?? 'all');
                      setPage(1);
                    }}
                    size="sm"
                  />
                </div>
              </TableToolbarContent>
            </TableToolbar>
            <Table {...getTableProps()}>
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
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">Loading users...</div>
                    </TableCell>
                  </TableRow>
                ) : tableRowsProp.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">No users found.</div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRowsProp.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const original = users.find((u) => u.id === row.id);
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'role' && original ? (
                              <Tag type={roleColor(original.role)} size="sm">
                                {roleLabel(original.role)}
                              </Tag>
                            ) : cell.info.header === 'status' && original ? (
                              <StatusTag type={original.isActive ? 'green' : 'red'}>
                                {original.isActive ? 'Active' : 'Inactive'}
                              </StatusTag>
                            ) : cell.info.header === 'createdAt' && original ? (
                              formatDate(original.createdAt)
                            ) : cell.info.header === 'actions' && original && canManage && original.isActive ? (
                              <Button
                                kind="danger--ghost"
                                size="sm"
                                onClick={() => handleDeactivate(original.id)}
                                disabled={deactivateUser.isPending}
                              >
                                Deactivate
                              </Button>
                            ) : (
                              cell.value
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DataTable>

      {total > perPage && (
        <Pagination
          totalItems={total}
          pageSize={perPage}
          pageSizes={[10, 20, 50]}
          page={page}
          onChange={({ page: p, pageSize }) => {
            setPage(p);
            setPerPage(pageSize);
          }}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Invites Tab
// ---------------------------------------------------------------------------

function InvitesTab({
  subBrands,
  onToast,
}: {
  subBrands: SubBrand[];
  onToast: (kind: 'success' | 'error', message: string) => void;
}) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const { data, isLoading, isError } = useInvites(page, perPage);
  const deleteInvite = useDeleteInvite();

  const invites: Invite[] = data?.data ?? [];
  const total = Number(data?.meta?.total ?? 0);

  const subBrandMap = new Map(subBrands.map((sb) => [sb.id, sb.name]));

  const tableHeaders = [
    { key: 'email', header: 'Email' },
    { key: 'role', header: 'Role' },
    { key: 'subBrand', header: 'Sub-Brand' },
    { key: 'status', header: 'Status' },
    { key: 'token', header: 'Token' },
    { key: 'createdAt', header: 'Created' },
    { key: 'actions', header: '' },
  ];

  const tableRows = invites.map((inv) => ({
    id: inv.id,
    email: inv.email,
    role: inv.role,
    subBrand: subBrandMap.get(inv.targetSubBrandId) ?? inv.targetSubBrandId,
    status: inviteStatus(inv),
    token: inv.token,
    createdAt: inv.createdAt,
  }));

  const handleDelete = (inviteId: string) => {
    deleteInvite.mutate(inviteId, {
      onSuccess: () => onToast('success', 'Invite deleted'),
      onError: () => onToast('error', 'Failed to delete invite'),
    });
  };

  return (
    <>
      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load invites"
          subtitle="Please try refreshing the page."
          hideCloseButton
        />
      )}

      <DataTable rows={tableRows} headers={tableHeaders} isSortable={false}>
        {({ rows: tableRowsProp, headers, getHeaderProps, getRowProps, getTableProps }) => (
          <TableContainer>
            <Table {...getTableProps()}>
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
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">Loading invites...</div>
                    </TableCell>
                  </TableRow>
                ) : tableRowsProp.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">No invites found.</div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRowsProp.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const original = invites.find((inv) => inv.id === row.id);
                    const status = original ? inviteStatus(original) : 'pending';
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'role' && original ? (
                              <Tag type={roleColor(original.role)} size="sm">
                                {roleLabel(original.role)}
                              </Tag>
                            ) : cell.info.header === 'status' ? (
                              <StatusTag type={inviteStatusColor(status)}>
                                {status}
                              </StatusTag>
                            ) : cell.info.header === 'token' && original ? (
                              <code className="text-xs">{original.token}</code>
                            ) : cell.info.header === 'createdAt' && original ? (
                              formatDate(original.createdAt)
                            ) : cell.info.header === 'actions' && original && status === 'pending' ? (
                              <Button
                                kind="danger--ghost"
                                size="sm"
                                renderIcon={TrashCan}
                                hasIconOnly
                                iconDescription="Delete invite"
                                onClick={() => handleDelete(original.id)}
                                disabled={deleteInvite.isPending}
                              />
                            ) : (
                              cell.value
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DataTable>

      {total > perPage && (
        <Pagination
          totalItems={total}
          pageSize={perPage}
          pageSizes={[10, 20, 50]}
          page={page}
          onChange={({ page: p, pageSize }) => {
            setPage(p);
            setPerPage(pageSize);
          }}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Org Code Tab
// ---------------------------------------------------------------------------

function OrgCodeTab({
  onToast,
}: {
  onToast: (kind: 'success' | 'error', message: string) => void;
}) {
  const { data: orgCode, isLoading } = useCurrentOrgCode();
  const generateOrgCode = useGenerateOrgCode();
  const deactivateOrgCode = useDeactivateOrgCode();

  const handleGenerate = () => {
    generateOrgCode.mutate(undefined, {
      onSuccess: (res) => {
        const code = res.data?.code;
        onToast('success', code ? `New org code generated: ${code}` : 'Org code generated');
      },
      onError: () => onToast('error', 'Failed to generate org code'),
    });
  };

  const handleDeactivate = () => {
    if (!orgCode) return;
    deactivateOrgCode.mutate(orgCode.id, {
      onSuccess: () => onToast('success', 'Org code deactivated'),
      onError: () => onToast('error', 'Failed to deactivate org code'),
    });
  };

  const handleCopy = () => {
    if (!orgCode?.code) return;
    navigator.clipboard.writeText(orgCode.code);
    onToast('success', 'Org code copied to clipboard');
  };

  if (isLoading) {
    return <div className="py-8 text-center text-text-secondary">Loading...</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {orgCode ? (
        <div className="p-6 rounded-lg border" style={{ backgroundColor: 'var(--cds-layer-01)', borderColor: 'var(--cds-border-subtle-01)' }}>
          <p className="text-sm mb-2" style={{ color: 'var(--cds-text-secondary)' }}>
            Current Org Code
          </p>
          <div className="flex items-center gap-4">
            <span className="text-3xl font-mono font-bold tracking-widest" style={{ color: 'var(--cds-text-primary)' }}>
              {orgCode.code}
            </span>
            <Button kind="ghost" size="sm" renderIcon={Copy} hasIconOnly iconDescription="Copy code" onClick={handleCopy} />
            <Button
              kind="danger--ghost"
              size="sm"
              onClick={handleDeactivate}
              disabled={deactivateOrgCode.isPending}
            >
              Deactivate
            </Button>
          </div>
          <p className="text-xs mt-2" style={{ color: 'var(--cds-text-secondary)' }}>
            Created {formatDate(orgCode.createdAt)}
          </p>
        </div>
      ) : (
        <div
          className="p-6 rounded-lg border text-center"
          style={{ backgroundColor: 'var(--cds-layer-01)', borderColor: 'var(--cds-border-subtle-01)' }}
        >
          <p className="text-lg font-medium" style={{ color: 'var(--cds-text-primary)' }}>
            No Active Org Code
          </p>
          <p className="text-sm mt-1 mb-4" style={{ color: 'var(--cds-text-secondary)' }}>
            Generate an org code to allow employees to self-register for your company.
          </p>
          <Button kind="primary" onClick={handleGenerate} disabled={generateOrgCode.isPending}>
            {generateOrgCode.isPending ? 'Generating...' : 'Generate Org Code'}
          </Button>
        </div>
      )}

      {orgCode && (
        <Button
          kind="secondary"
          onClick={handleGenerate}
          disabled={generateOrgCode.isPending}
        >
          {generateOrgCode.isPending ? 'Generating...' : 'Generate New Code'}
        </Button>
      )}

      <InlineNotification
        kind="warning"
        title="Important"
        subtitle="Generating a new code will deactivate the previous one. Employees using the old code will no longer be able to register with it."
        hideCloseButton
        lowContrast
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function UsersPage() {
  const { user } = useAuth();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('employee');
  const [inviteSubBrandId, setInviteSubBrandId] = useState('');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  const createInvite = useCreateInvite();
  const { data: subBrandsData } = useSubBrands();
  const subBrands: SubBrand[] = subBrandsData?.data ?? [];

  const role = user?.tenantContext.role;
  const canManage = role ? CAN_MANAGE_USERS.includes(role) : false;
  const isCorporateAdmin = role === 'corporate_admin';
  const isSubBrandAdmin = role === 'sub_brand_admin';

  // Auto-set sub-brand for sub_brand_admin
  useEffect(() => {
    if (isSubBrandAdmin && user?.tenantContext.subBrandId) {
      setInviteSubBrandId(user.tenantContext.subBrandId);
    }
  }, [isSubBrandAdmin, user?.tenantContext.subBrandId]);

  const showToast = (kind: 'success' | 'error', message: string) => {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  };

  const resetInviteForm = () => {
    setInviteEmail('');
    setInviteRole('employee');
    if (isSubBrandAdmin && user?.tenantContext.subBrandId) {
      setInviteSubBrandId(user.tenantContext.subBrandId);
    } else {
      setInviteSubBrandId('');
    }
  };

  const handleInviteSubmit = () => {
    createInvite.mutate(
      { email: inviteEmail, targetSubBrandId: inviteSubBrandId, role: inviteRole },
      {
        onSuccess: () => {
          showToast('success', 'Invite sent successfully');
          setInviteOpen(false);
          resetInviteForm();
        },
        onError: () => {
          showToast('error', 'Failed to send invite');
        },
      },
    );
  };

  if (!user) return null;

  const subBrandDropdownItems = subBrands.filter((sb) => sb.isActive);

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <UserProfile size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">User Management</h1>
        </div>
        {canManage && (
          <Button kind="primary" size="sm" renderIcon={Add} onClick={() => setInviteOpen(true)}>
            Invite User
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs>
        <TabList aria-label="User management tabs">
          <Tab>Users</Tab>
          <Tab>Invites</Tab>
          {isCorporateAdmin && <Tab>Org Code</Tab>}
        </TabList>
        <TabPanels>
          <TabPanel>
            <div className="pt-4">
              <UsersTab canManage={canManage} onToast={showToast} />
            </div>
          </TabPanel>
          <TabPanel>
            <div className="pt-4">
              <InvitesTab subBrands={subBrands} onToast={showToast} />
            </div>
          </TabPanel>
          {isCorporateAdmin && (
            <TabPanel>
              <div className="pt-4">
                <OrgCodeTab onToast={showToast} />
              </div>
            </TabPanel>
          )}
        </TabPanels>
      </Tabs>

      {/* Invite Modal */}
      <Modal
        open={inviteOpen}
        onRequestClose={() => {
          setInviteOpen(false);
          resetInviteForm();
        }}
        onRequestSubmit={handleInviteSubmit}
        modalHeading="Invite User"
        primaryButtonText={createInvite.isPending ? 'Sending...' : 'Send Invite'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={!inviteEmail || !inviteSubBrandId || createInvite.isPending}
      >
        <div className="flex flex-col gap-4 mt-2">
          <TextInput
            id="invite-email"
            labelText="Email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            required
          />
          {!isSubBrandAdmin && (
            <Dropdown
              id="invite-sub-brand"
              titleText="Sub-Brand"
              label="Select sub-brand"
              items={subBrandDropdownItems}
              itemToString={(item) => item?.name ?? ''}
              onChange={({ selectedItem }) => setInviteSubBrandId(selectedItem?.id ?? '')}
              selectedItem={subBrandDropdownItems.find((sb) => sb.id === inviteSubBrandId) ?? null}
            />
          )}
          {isSubBrandAdmin && (
            <TextInput
              id="invite-sub-brand-display"
              labelText="Sub-Brand"
              value={subBrands.find((sb) => sb.id === inviteSubBrandId)?.name ?? ''}
              readOnly
            />
          )}
          <Dropdown
            id="invite-role"
            titleText="Role"
            label="Select role"
            items={INVITE_ROLE_OPTIONS}
            itemToString={(item) => item?.text ?? ''}
            initialSelectedItem={INVITE_ROLE_OPTIONS[0]}
            onChange={({ selectedItem }) => setInviteRole(selectedItem?.id ?? 'employee')}
          />
        </div>
      </Modal>

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
