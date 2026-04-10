'use client';

import { useState } from 'react';
import {
  Button,
  DataTable,
  Dropdown,
  InlineNotification,
  Modal,
  Pagination,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  TableToolbar,
  TableToolbarContent,
  Tag,
  TextInput,
  ToastNotification,
} from '@carbon/react';
import { UserProfile, Add } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/hooks';
import type { UserRole } from '@/types/auth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  subBrandId: string | null;
  subBrandName?: string;
  isActive: boolean;
  createdAt: string;
}

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

function roleLabel(role: UserRole): string {
  return role.replace(/_/g, ' ');
}

function roleColor(role: UserRole): 'purple' | 'teal' | 'blue' | 'green' | 'gray' {
  switch (role) {
    case 'corporate_admin': return 'purple';
    case 'sub_brand_admin': return 'teal';
    case 'regional_manager': return 'blue';
    case 'employee': return 'green';
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

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useUsers(page: number, perPage: number, roleFilter: string) {
  const params: Record<string, string> = {
    page: String(page),
    per_page: String(perPage),
  };
  if (roleFilter !== 'all') params.role = roleFilter;

  return useQuery({
    queryKey: ['users', page, perPage, roleFilter],
    queryFn: async () => {
      const res = await api.get<User[]>('/api/v1/users/', params);
      return res;
    },
  });
}

function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/api/v1/users/${userId}/deactivate`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

function useInviteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { email: string; fullName: string; role: string }) => {
      await api.post('/api/v1/invites/', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const CAN_MANAGE_USERS: UserRole[] = ['corporate_admin', 'sub_brand_admin'];

export default function UsersPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [roleFilter, setRoleFilter] = useState('all');
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState('employee');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  const { data, isLoading, isError } = useUsers(page, perPage, roleFilter);
  const deactivateUser = useDeactivateUser();
  const inviteUser = useInviteUser();

  const canManage = user && CAN_MANAGE_USERS.includes(user.tenantContext.role);

  const users = data?.data ?? [];
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

  const handleInvite = () => {
    inviteUser.mutate(
      { email: inviteEmail, fullName: inviteName, role: inviteRole },
      {
        onSuccess: () => {
          setToast({ kind: 'success', message: 'Invite sent successfully' });
          setInviteOpen(false);
          setInviteEmail('');
          setInviteName('');
          setInviteRole('employee');
          setTimeout(() => setToast(null), 3000);
        },
        onError: () => {
          setToast({ kind: 'error', message: 'Failed to send invite' });
          setTimeout(() => setToast(null), 3000);
        },
      },
    );
  };

  const handleDeactivate = (userId: string) => {
    deactivateUser.mutate(userId, {
      onSuccess: () => {
        setToast({ kind: 'success', message: 'User deactivated' });
        setTimeout(() => setToast(null), 3000);
      },
    });
  };

  if (!user) return null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <UserProfile size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">Users</h1>
        </div>
        {canManage && (
          <Button
            kind="primary"
            size="sm"
            renderIcon={Add}
            onClick={() => setInviteOpen(true)}
          >
            Invite User
          </Button>
        )}
      </div>

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
                <div className="flex gap-4 items-end">
                  <Dropdown
                    id="role-filter"
                    titleText="Filter by Role"
                    label="Select role"
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
                              <Tag type={original.isActive ? 'green' : 'red'} size="sm">
                                {original.isActive ? 'Active' : 'Inactive'}
                              </Tag>
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

      {/* Invite Modal */}
      <Modal
        open={inviteOpen}
        onRequestClose={() => setInviteOpen(false)}
        onRequestSubmit={handleInvite}
        modalHeading="Invite User"
        primaryButtonText={inviteUser.isPending ? 'Sending...' : 'Send Invite'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={!inviteEmail || !inviteName || inviteUser.isPending}
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
          <TextInput
            id="invite-name"
            labelText="Full Name"
            value={inviteName}
            onChange={(e) => setInviteName(e.target.value)}
            required
          />
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
