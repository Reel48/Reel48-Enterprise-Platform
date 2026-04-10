'use client';

import { useState } from 'react';
import {
  Button,
  DataTable,
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
import { Store, Add } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SubBrand {
  id: string;
  name: string;
  slug: string;
  isDefault: boolean;
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

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function useSubBrands(page: number, perPage: number) {
  return useQuery({
    queryKey: ['sub-brands', page, perPage],
    queryFn: async () => {
      const res = await api.get<SubBrand[]>('/api/v1/sub_brands/', {
        page: String(page),
        per_page: String(perPage),
      });
      return res;
    },
  });
}

function useCreateSubBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string }) => {
      const res = await api.post<SubBrand>('/api/v1/sub_brands/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sub-brands'] });
    },
  });
}

function useDeactivateSubBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/sub_brands/${id}/deactivate`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sub-brands'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BrandsPage() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [createOpen, setCreateOpen] = useState(false);
  const [brandName, setBrandName] = useState('');
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  const { data, isLoading, isError } = useSubBrands(page, perPage);
  const createSubBrand = useCreateSubBrand();
  const deactivateSubBrand = useDeactivateSubBrand();

  const brands = data?.data ?? [];
  const total = Number(data?.meta?.total ?? 0);

  const tableHeaders = [
    { key: 'name', header: 'Name' },
    { key: 'slug', header: 'Slug' },
    { key: 'isDefault', header: 'Default' },
    { key: 'status', header: 'Status' },
    { key: 'createdAt', header: 'Created' },
    { key: 'actions', header: '' },
  ];

  const tableRows = brands.map((b) => ({
    id: b.id,
    name: b.name,
    slug: b.slug,
    isDefault: b.isDefault,
    status: b.isActive,
    createdAt: b.createdAt,
  }));

  const handleCreate = () => {
    createSubBrand.mutate(
      { name: brandName.trim() },
      {
        onSuccess: () => {
          setToast({ kind: 'success', message: 'Sub-brand created' });
          setCreateOpen(false);
          setBrandName('');
          setTimeout(() => setToast(null), 3000);
        },
        onError: () => {
          setToast({ kind: 'error', message: 'Failed to create sub-brand' });
          setTimeout(() => setToast(null), 3000);
        },
      },
    );
  };

  const handleDeactivate = (id: string) => {
    deactivateSubBrand.mutate(id, {
      onSuccess: () => {
        setToast({ kind: 'success', message: 'Sub-brand deactivated' });
        setTimeout(() => setToast(null), 3000);
      },
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Store size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">Sub-Brands</h1>
        </div>
        <Button
          kind="primary"
          size="sm"
          renderIcon={Add}
          onClick={() => setCreateOpen(true)}
        >
          Create Sub-Brand
        </Button>
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load sub-brands"
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
                      <div className="py-8 text-center text-text-secondary">Loading sub-brands...</div>
                    </TableCell>
                  </TableRow>
                ) : tableRowsProp.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">No sub-brands found.</div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRowsProp.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const original = brands.find((b) => b.id === row.id);
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'isDefault' && original ? (
                              original.isDefault ? (
                                <Tag type="blue" size="sm">Default</Tag>
                              ) : (
                                '—'
                              )
                            ) : cell.info.header === 'status' && original ? (
                              <Tag type={original.isActive ? 'green' : 'red'} size="sm">
                                {original.isActive ? 'Active' : 'Inactive'}
                              </Tag>
                            ) : cell.info.header === 'createdAt' && original ? (
                              formatDate(original.createdAt)
                            ) : cell.info.header === 'actions' && original && original.isActive && !original.isDefault ? (
                              <Button
                                kind="danger--ghost"
                                size="sm"
                                onClick={() => handleDeactivate(original.id)}
                                disabled={deactivateSubBrand.isPending}
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

      {/* Create Modal */}
      <Modal
        open={createOpen}
        onRequestClose={() => setCreateOpen(false)}
        onRequestSubmit={handleCreate}
        modalHeading="Create Sub-Brand"
        primaryButtonText={createSubBrand.isPending ? 'Creating...' : 'Create'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={!brandName.trim() || createSubBrand.isPending}
      >
        <div className="flex flex-col gap-4 mt-2">
          <TextInput
            id="brand-name"
            labelText="Sub-Brand Name"
            placeholder="e.g., North Division"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            required
            helperText="A URL-safe slug will be generated automatically"
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
