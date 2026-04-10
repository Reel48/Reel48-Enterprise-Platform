'use client';

import { useState } from 'react';
import {
  Button,
  DataTable,
  Dropdown,
  InlineNotification,
  Modal,
  Pagination,
  Search,
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
import { Add, Enterprise } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type { Company } from '@/types/companies';

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

const STATUS_OPTIONS = [
  { id: 'all', text: 'All' },
  { id: 'active', text: 'Active' },
  { id: 'inactive', text: 'Inactive' },
];

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useCompanies(page: number, perPage: number, search: string, status: string) {
  return useQuery({
    queryKey: ['platform-companies', page, perPage, search, status],
    queryFn: async () => {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (search) params.search = search;
      if (status && status !== 'all') params.is_active = status === 'active' ? 'true' : 'false';
      const res = await api.get<Company[]>('/api/v1/platform/companies/', params);
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

function useCreateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string }) => {
      const res = await api.post<Company>('/api/v1/platform/companies/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] });
    },
  });
}

function useDeactivateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (companyId: string) => {
      await api.post(`/api/v1/platform/companies/${companyId}/deactivate`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Table config
// ---------------------------------------------------------------------------

const tableHeaders = [
  { key: 'name', header: 'Company Name' },
  { key: 'slug', header: 'Slug' },
  { key: 'isActive', header: 'Status' },
  { key: 'createdAt', header: 'Created' },
  { key: 'actions', header: '' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PlatformCompaniesPage() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  const { data, isLoading, isError } = useCompanies(page, perPage, search, statusFilter);
  const createCompany = useCreateCompany();
  const deactivateCompany = useDeactivateCompany();

  const companies = data?.data ?? [];
  const total = data?.total ?? 0;

  const rows = companies.map((c) => ({
    id: c.id,
    name: c.name,
    slug: c.slug,
    isActive: c.isActive,
    createdAt: c.createdAt,
  }));

  const handleCreate = () => {
    if (!newName.trim()) return;
    createCompany.mutate(
      { name: newName },
      {
        onSuccess: () => {
          setCreateModalOpen(false);
          setNewName('');
          setToast({ kind: 'success', message: 'Company created successfully' });
          setTimeout(() => setToast(null), 3000);
        },
        onError: () => {
          setToast({ kind: 'error', message: 'Failed to create company' });
          setTimeout(() => setToast(null), 3000);
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">
          Companies
        </h1>
        <Button
          kind="primary"
          size="sm"
          renderIcon={Add}
          onClick={() => setCreateModalOpen(true)}
        >
          Create Company
        </Button>
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load companies"
          hideCloseButton
        />
      )}

      <DataTable rows={rows} headers={tableHeaders} isSortable={false}>
        {({ rows: tRows, headers: tHeaders, getHeaderProps, getRowProps, getTableProps }) => (
          <TableContainer>
            <TableToolbar>
              <TableToolbarContent>
                <Search
                  id="company-search"
                  labelText=""
                  placeholder="Search companies..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  size="sm"
                />
                <Dropdown
                  id="company-status-filter"
                  titleText=""
                  label="Status"
                  items={STATUS_OPTIONS}
                  itemToString={(item: { id: string; text: string } | null) => item?.text ?? ''}
                  selectedItem={STATUS_OPTIONS.find((s) => s.id === statusFilter) ?? STATUS_OPTIONS[0]}
                  onChange={({ selectedItem }: { selectedItem: { id: string; text: string } | null }) => {
                    setStatusFilter(selectedItem?.id ?? 'all');
                    setPage(1);
                  }}
                  size="sm"
                />
              </TableToolbarContent>
            </TableToolbar>
            <Table {...getTableProps()}>
              <TableHead>
                <TableRow>
                  {tHeaders.map((header) => {
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
                      <div className="py-8 text-center text-text-secondary">
                        Loading companies...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : companies.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center">
                        <Enterprise size={48} className="mx-auto mb-4 text-text-secondary" />
                        <p className="text-lg font-medium text-text-primary">
                          No companies found
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tRows.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const company = companies.find((c) => c.id === row.id);
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => {
                          if (cell.info.header === 'isActive') {
                            return (
                              <TableCell key={cell.id}>
                                <Tag type={cell.value ? 'green' : 'red'} size="sm">
                                  {cell.value ? 'Active' : 'Inactive'}
                                </Tag>
                              </TableCell>
                            );
                          }
                          if (cell.info.header === 'createdAt') {
                            return (
                              <TableCell key={cell.id}>
                                {formatDate(cell.value as string)}
                              </TableCell>
                            );
                          }
                          if (cell.info.header === 'actions') {
                            return (
                              <TableCell key={cell.id}>
                                <div className="flex gap-2">
                                  <Button kind="ghost" size="sm" href={`/platform/companies/${row.id}`}>
                                    View
                                  </Button>
                                  {company?.isActive && (
                                    <Button
                                      kind="danger--ghost"
                                      size="sm"
                                      onClick={() => deactivateCompany.mutate(row.id)}
                                      disabled={deactivateCompany.isPending}
                                    >
                                      Deactivate
                                    </Button>
                                  )}
                                </div>
                              </TableCell>
                            );
                          }
                          return <TableCell key={cell.id}>{cell.value as string}</TableCell>;
                        })}
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
          page={page}
          pageSize={perPage}
          pageSizes={[10, 20, 50]}
          totalItems={total}
          onChange={({ page: p, pageSize }: { page: number; pageSize: number }) => {
            setPage(p);
            setPerPage(pageSize);
          }}
        />
      )}

      {/* Create Company Modal */}
      <Modal
        open={createModalOpen}
        modalHeading="Create Company"
        primaryButtonText="Create"
        secondaryButtonText="Cancel"
        onRequestSubmit={handleCreate}
        onRequestClose={() => {
          setCreateModalOpen(false);
          setNewName('');
        }}
        primaryButtonDisabled={!newName.trim() || createCompany.isPending}
      >
        <div className="flex flex-col gap-4">
          <TextInput
            id="company-name"
            labelText="Company Name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
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
