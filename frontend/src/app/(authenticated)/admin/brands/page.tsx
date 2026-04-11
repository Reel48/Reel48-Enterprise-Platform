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
  TextInput,
  ToastNotification,
} from '@carbon/react';
import { Store, Add, Edit, TrashCan } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import { StatusTag } from '@/components/ui/StatusTag';

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

function useUpdateSubBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: { name: string } }) => {
      const res = await api.patch<SubBrand>(`/api/v1/sub_brands/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sub-brands'] });
    },
  });
}

function useDeleteSubBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/sub_brands/${id}`);
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

  // Edit modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editBrand, setEditBrand] = useState<SubBrand | null>(null);
  const [editName, setEditName] = useState('');

  // Delete modal state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteBrand, setDeleteBrand] = useState<SubBrand | null>(null);

  const { data, isLoading, isError } = useSubBrands(page, perPage);
  const createSubBrand = useCreateSubBrand();
  const updateSubBrand = useUpdateSubBrand();
  const deleteSubBrand = useDeleteSubBrand();
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

  const showToast = (kind: 'success' | 'error', message: string) => {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  };

  const handleCreate = () => {
    createSubBrand.mutate(
      { name: brandName.trim() },
      {
        onSuccess: () => {
          showToast('success', 'Sub-brand created');
          setCreateOpen(false);
          setBrandName('');
        },
        onError: () => {
          showToast('error', 'Failed to create sub-brand');
        },
      },
    );
  };

  const openEdit = (brand: SubBrand) => {
    setEditBrand(brand);
    setEditName(brand.name);
    setEditOpen(true);
  };

  const handleEdit = () => {
    if (!editBrand || !editName.trim()) return;
    updateSubBrand.mutate(
      { id: editBrand.id, data: { name: editName.trim() } },
      {
        onSuccess: () => {
          showToast('success', 'Sub-brand updated');
          setEditOpen(false);
          setEditBrand(null);
        },
        onError: () => {
          showToast('error', 'Failed to update sub-brand');
        },
      },
    );
  };

  const handleDelete = () => {
    if (!deleteBrand) return;
    deleteSubBrand.mutate(deleteBrand.id, {
      onSuccess: () => {
        showToast('success', 'Sub-brand deleted');
        setDeleteOpen(false);
        setDeleteBrand(null);
      },
      onError: () => {
        showToast('error', 'Failed to delete sub-brand');
      },
    });
  };

  const handleDeactivate = (id: string) => {
    deactivateSubBrand.mutate(id, {
      onSuccess: () => {
        showToast('success', 'Sub-brand deactivated');
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
                                <StatusTag type="blue">Default</StatusTag>
                              ) : (
                                '—'
                              )
                            ) : cell.info.header === 'status' && original ? (
                              <StatusTag type={original.isActive ? 'green' : 'red'}>
                                {original.isActive ? 'Active' : 'Inactive'}
                              </StatusTag>
                            ) : cell.info.header === 'createdAt' && original ? (
                              formatDate(original.createdAt)
                            ) : cell.info.header === 'actions' && original ? (
                              <div className="flex gap-2">
                                <Button
                                  kind="ghost"
                                  size="sm"
                                  renderIcon={Edit}
                                  iconDescription="Edit"
                                  hasIconOnly
                                  onClick={() => openEdit(original)}
                                />
                                {original.isActive && !original.isDefault && (
                                  <Button
                                    kind="danger--ghost"
                                    size="sm"
                                    onClick={() => handleDeactivate(original.id)}
                                    disabled={deactivateSubBrand.isPending}
                                  >
                                    Deactivate
                                  </Button>
                                )}
                                {!original.isDefault && (
                                  <Button
                                    kind="danger--ghost"
                                    size="sm"
                                    renderIcon={TrashCan}
                                    iconDescription="Delete"
                                    hasIconOnly
                                    onClick={() => {
                                      setDeleteBrand(original);
                                      setDeleteOpen(true);
                                    }}
                                  />
                                )}
                              </div>
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

      {/* Edit Modal */}
      <Modal
        open={editOpen}
        onRequestClose={() => {
          setEditOpen(false);
          setEditBrand(null);
        }}
        onRequestSubmit={handleEdit}
        modalHeading="Edit Sub-Brand"
        primaryButtonText={updateSubBrand.isPending ? 'Saving...' : 'Save'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={!editName.trim() || updateSubBrand.isPending}
      >
        <div className="flex flex-col gap-4 mt-2">
          <TextInput
            id="edit-brand-name"
            labelText="Sub-Brand Name"
            placeholder="e.g., North Division"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={deleteOpen}
        onRequestClose={() => {
          setDeleteOpen(false);
          setDeleteBrand(null);
        }}
        onRequestSubmit={handleDelete}
        modalHeading="Delete Sub-Brand"
        primaryButtonText={deleteSubBrand.isPending ? 'Deleting...' : 'Delete'}
        secondaryButtonText="Cancel"
        danger
        primaryButtonDisabled={deleteSubBrand.isPending}
      >
        {deleteBrand && (
          <p>
            Are you sure you want to delete <strong>{deleteBrand.name}</strong>? This cannot be
            undone.
          </p>
        )}
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
