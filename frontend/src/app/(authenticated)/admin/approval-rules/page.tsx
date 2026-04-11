'use client';

import { useState } from 'react';
import {
  Button,
  DataTable,
  Dropdown,
  InlineNotification,
  Modal,
  NumberInput,
  Pagination,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  ToastNotification,
  Toggle,
} from '@carbon/react';
import { Policy, Add, Edit, TrashCan } from '@carbon/react/icons';

import {
  useApprovalRules,
  useCreateApprovalRule,
  useUpdateApprovalRule,
  useDeleteApprovalRule,
} from './_hooks';
import type { ApprovalRule } from './_hooks';
import { StatusTag } from '@/components/ui/StatusTag';

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

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  order: 'Order',
  bulk_order: 'Bulk Order',
};

const ROLE_LABELS: Record<string, string> = {
  corporate_admin: 'Corporate Admin',
  sub_brand_admin: 'Sub-Brand Admin',
  regional_manager: 'Regional Manager',
};

const ENTITY_TYPE_ITEMS = [
  { id: 'order', text: 'Order' },
  { id: 'bulk_order', text: 'Bulk Order' },
];

const ROLE_ITEMS = [
  { id: 'corporate_admin', text: 'Corporate Admin' },
  { id: 'sub_brand_admin', text: 'Sub-Brand Admin' },
  { id: 'regional_manager', text: 'Regional Manager' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ApprovalRulesPage() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  // Create modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [createEntityType, setCreateEntityType] = useState<string | null>(null);
  const [createThreshold, setCreateThreshold] = useState<number | ''>('');
  const [createRole, setCreateRole] = useState<string | null>(null);

  // Edit modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editRule, setEditRule] = useState<ApprovalRule | null>(null);
  const [editThreshold, setEditThreshold] = useState<number | ''>('');
  const [editRole, setEditRole] = useState<string | null>(null);
  const [editIsActive, setEditIsActive] = useState(true);

  // Delete modal state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteRule, setDeleteRule] = useState<ApprovalRule | null>(null);

  const { data, isLoading, isError } = useApprovalRules(page, perPage);
  const createMutation = useCreateApprovalRule();
  const updateMutation = useUpdateApprovalRule();
  const deleteMutation = useDeleteApprovalRule();

  const rules = data?.data ?? [];
  const total = Number(data?.meta?.total ?? 0);

  const showToast = (kind: 'success' | 'error', message: string) => {
    setToast({ kind, message });
    setTimeout(() => setToast(null), 3000);
  };

  // ---- Create ----

  const resetCreateForm = () => {
    setCreateEntityType(null);
    setCreateThreshold('');
    setCreateRole(null);
  };

  const handleCreate = () => {
    if (!createEntityType || createThreshold === '' || !createRole) return;
    createMutation.mutate(
      {
        entityType: createEntityType,
        ruleType: 'amount_threshold',
        thresholdAmount: Number(createThreshold),
        requiredRole: createRole,
      },
      {
        onSuccess: () => {
          showToast('success', 'Approval rule created');
          setCreateOpen(false);
          resetCreateForm();
        },
        onError: () => {
          showToast('error', 'Failed to create approval rule');
        },
      },
    );
  };

  // ---- Edit ----

  const openEdit = (rule: ApprovalRule) => {
    setEditRule(rule);
    setEditThreshold(rule.thresholdAmount);
    setEditRole(rule.requiredRole);
    setEditIsActive(rule.isActive);
    setEditOpen(true);
  };

  const handleEdit = () => {
    if (!editRule || editThreshold === '' || !editRole) return;
    updateMutation.mutate(
      {
        id: editRule.id,
        data: {
          thresholdAmount: Number(editThreshold),
          requiredRole: editRole,
          isActive: editIsActive,
        },
      },
      {
        onSuccess: () => {
          showToast('success', 'Approval rule updated');
          setEditOpen(false);
          setEditRule(null);
        },
        onError: () => {
          showToast('error', 'Failed to update approval rule');
        },
      },
    );
  };

  // ---- Toggle active ----

  const handleToggleActive = (rule: ApprovalRule) => {
    updateMutation.mutate(
      { id: rule.id, data: { isActive: !rule.isActive } },
      {
        onSuccess: () => {
          showToast('success', rule.isActive ? 'Rule deactivated' : 'Rule activated');
        },
        onError: () => {
          showToast('error', 'Failed to update rule');
        },
      },
    );
  };

  // ---- Delete ----

  const handleDelete = () => {
    if (!deleteRule) return;
    deleteMutation.mutate(deleteRule.id, {
      onSuccess: () => {
        showToast('success', 'Approval rule deleted');
        setDeleteOpen(false);
        setDeleteRule(null);
      },
      onError: () => {
        showToast('error', 'Failed to delete approval rule');
      },
    });
  };

  // ---- Table ----

  const tableHeaders = [
    { key: 'entityType', header: 'Entity Type' },
    { key: 'thresholdAmount', header: 'Threshold Amount' },
    { key: 'requiredRole', header: 'Required Role' },
    { key: 'isActive', header: 'Active' },
    { key: 'createdAt', header: 'Created' },
    { key: 'actions', header: '' },
  ];

  const tableRows = rules.map((r) => ({
    id: r.id,
    entityType: r.entityType,
    thresholdAmount: r.thresholdAmount,
    requiredRole: r.requiredRole,
    isActive: r.isActive,
    createdAt: r.createdAt,
  }));

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Policy size={24} className="text-interactive" />
          <h1 className="text-2xl font-semibold text-text-primary">Approval Rules</h1>
        </div>
        <Button kind="primary" size="sm" renderIcon={Add} onClick={() => setCreateOpen(true)}>
          Create Rule
        </Button>
      </div>

      {isError && (
        <InlineNotification
          kind="error"
          title="Failed to load approval rules"
          subtitle="Please try refreshing the page."
          hideCloseButton
        />
      )}

      {/* DataTable */}
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
                      <div className="py-8 text-center text-text-secondary">Loading approval rules...</div>
                    </TableCell>
                  </TableRow>
                ) : tableRowsProp.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={tableHeaders.length}>
                      <div className="py-8 text-center text-text-secondary">
                        No approval rules found. Create one to get started.
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  tableRowsProp.map((row) => {
                    const { key: rowKey, ...rowProps } = getRowProps({ row });
                    const original = rules.find((r) => r.id === row.id);
                    return (
                      <TableRow key={String(rowKey)} {...rowProps}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'entityType' && original ? (
                              ENTITY_TYPE_LABELS[original.entityType] || original.entityType
                            ) : cell.info.header === 'thresholdAmount' && original ? (
                              formatCurrency(original.thresholdAmount)
                            ) : cell.info.header === 'requiredRole' && original ? (
                              ROLE_LABELS[original.requiredRole] || original.requiredRole
                            ) : cell.info.header === 'isActive' && original ? (
                              <StatusTag type={original.isActive ? 'green' : 'gray'}>
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
                                <Button
                                  kind="ghost"
                                  size="sm"
                                  onClick={() => handleToggleActive(original)}
                                  disabled={updateMutation.isPending}
                                >
                                  {original.isActive ? 'Deactivate' : 'Activate'}
                                </Button>
                                <Button
                                  kind="danger--ghost"
                                  size="sm"
                                  renderIcon={TrashCan}
                                  iconDescription="Delete"
                                  hasIconOnly
                                  onClick={() => {
                                    setDeleteRule(original);
                                    setDeleteOpen(true);
                                  }}
                                />
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
        onRequestClose={() => {
          setCreateOpen(false);
          resetCreateForm();
        }}
        onRequestSubmit={handleCreate}
        modalHeading="Create Approval Rule"
        primaryButtonText={createMutation.isPending ? 'Creating...' : 'Create'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={
          !createEntityType || createThreshold === '' || !createRole || createMutation.isPending
        }
      >
        <div className="flex flex-col gap-6 mt-2">
          <Dropdown
            id="create-entity-type"
            titleText="Entity Type"
            label="Select entity type"
            items={ENTITY_TYPE_ITEMS}
            itemToString={(item) => item?.text ?? ''}
            onChange={({ selectedItem }) => setCreateEntityType(selectedItem?.id ?? null)}
          />
          <NumberInput
            id="create-threshold"
            label="Threshold Amount ($)"
            min={0}
            step={100}
            value={createThreshold}
            onChange={(_e: unknown, { value }: { value: number | string }) =>
              setCreateThreshold(value === '' ? '' : Number(value))
            }
            helperText="Orders above this amount will require approval"
          />
          <Dropdown
            id="create-required-role"
            titleText="Required Role"
            label="Select required approver role"
            items={ROLE_ITEMS}
            itemToString={(item) => item?.text ?? ''}
            onChange={({ selectedItem }) => setCreateRole(selectedItem?.id ?? null)}
          />
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal
        open={editOpen}
        onRequestClose={() => {
          setEditOpen(false);
          setEditRule(null);
        }}
        onRequestSubmit={handleEdit}
        modalHeading="Edit Approval Rule"
        primaryButtonText={updateMutation.isPending ? 'Saving...' : 'Save'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={editThreshold === '' || !editRole || updateMutation.isPending}
      >
        {editRule && (
          <div className="flex flex-col gap-6 mt-2">
            <div>
              <p className="text-sm text-text-secondary mb-1">Entity Type</p>
              <p className="text-sm font-medium text-text-primary">
                {ENTITY_TYPE_LABELS[editRule.entityType] || editRule.entityType}
              </p>
            </div>
            <NumberInput
              id="edit-threshold"
              label="Threshold Amount ($)"
              min={0}
              step={100}
              value={editThreshold}
              onChange={(_e: unknown, { value }: { value: number | string }) =>
                setEditThreshold(value === '' ? '' : Number(value))
              }
            />
            <Dropdown
              id="edit-required-role"
              titleText="Required Role"
              label="Select required approver role"
              items={ROLE_ITEMS}
              selectedItem={ROLE_ITEMS.find((r) => r.id === editRole) ?? null}
              itemToString={(item) => item?.text ?? ''}
              onChange={({ selectedItem }) => setEditRole(selectedItem?.id ?? null)}
            />
            <Toggle
              id="edit-is-active"
              labelText="Active"
              labelA="Inactive"
              labelB="Active"
              toggled={editIsActive}
              onToggle={(toggled) => setEditIsActive(toggled)}
            />
          </div>
        )}
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={deleteOpen}
        onRequestClose={() => {
          setDeleteOpen(false);
          setDeleteRule(null);
        }}
        onRequestSubmit={handleDelete}
        modalHeading="Delete Approval Rule"
        primaryButtonText={deleteMutation.isPending ? 'Deleting...' : 'Delete'}
        secondaryButtonText="Cancel"
        danger
        primaryButtonDisabled={deleteMutation.isPending}
      >
        {deleteRule && (
          <p>
            Are you sure you want to delete the{' '}
            <strong>{ENTITY_TYPE_LABELS[deleteRule.entityType]}</strong> approval rule with a
            threshold of <strong>{formatCurrency(deleteRule.thresholdAmount)}</strong>? This action
            cannot be undone.
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
