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
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Tag,
  TextArea,
} from '@carbon/react';
import { Checkmark, Close, Policy, Task } from '@carbon/react/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';

import { api } from '@/lib/api/client';
import { useHasRole } from '@/lib/auth/hooks';
import { StatusTag } from '@/components/ui/StatusTag';
import type { ApprovalRequest } from '@/types/approvals';

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

function statusColor(status: string): 'teal' | 'purple' | 'green' | 'red' | 'gray' {
  switch (status) {
    case 'approved':
      return 'green';
    case 'pending':
      return 'purple';
    case 'rejected':
      return 'red';
    default:
      return 'gray';
  }
}

function requestTypeLabel(type: string): string {
  switch (type) {
    case 'order':
      return 'Order';
    case 'bulk_order':
      return 'Bulk Order';
    case 'catalog':
      return 'Catalog';
    default:
      return type;
  }
}

// ---------------------------------------------------------------------------
// Data hooks
// ---------------------------------------------------------------------------

function usePendingApprovals(page: number, perPage: number) {
  return useQuery({
    queryKey: ['approvals-pending', page, perPage],
    queryFn: async () => {
      const res = await api.get<ApprovalRequest[]>('/api/v1/approvals/pending/', {
        page: String(page),
        per_page: String(perPage),
      });
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

function useApprovalHistory(page: number, perPage: number) {
  return useQuery({
    queryKey: ['approvals-history', page, perPage],
    queryFn: async () => {
      const res = await api.get<ApprovalRequest[]>('/api/v1/approvals/history/', {
        page: String(page),
        per_page: String(perPage),
      });
      return {
        data: res.data,
        total: (res.meta as { total?: number })?.total ?? 0,
      };
    },
  });
}

function useApproveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (approvalId: string) => {
      await api.post(`/api/v1/approvals/${approvalId}/approve`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals-pending'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-history'] });
    },
  });
}

function useRejectRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ approvalId, reason }: { approvalId: string; reason: string }) => {
      await api.post(`/api/v1/approvals/${approvalId}/reject`, { reason });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals-pending'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-history'] });
    },
  });
}

// ---------------------------------------------------------------------------
// Table configs
// ---------------------------------------------------------------------------

const pendingHeaders = [
  { key: 'entityType', header: 'Type' },
  { key: 'requestedBy', header: 'Requester' },
  { key: 'createdAt', header: 'Submitted' },
  { key: 'actions', header: '' },
];

const historyHeaders = [
  { key: 'entityType', header: 'Type' },
  { key: 'requestedBy', header: 'Requester' },
  { key: 'status', header: 'Decision' },
  { key: 'decidedBy', header: 'Decided By' },
  { key: 'decidedAt', header: 'Date' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ApprovalsPage() {
  const isCorporateAdmin = useHasRole(['corporate_admin']);
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingPerPage, setPendingPerPage] = useState(20);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPerPage, setHistoryPerPage] = useState(20);

  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const pending = usePendingApprovals(pendingPage, pendingPerPage);
  const history = useApprovalHistory(historyPage, historyPerPage);
  const approveRequest = useApproveRequest();
  const rejectRequest = useRejectRequest();

  const pendingItems = pending.data?.data ?? [];
  const pendingTotal = pending.data?.total ?? 0;
  const historyItems = history.data?.data ?? [];
  const historyTotal = history.data?.total ?? 0;

  const handleReject = () => {
    if (!rejectTarget) return;
    rejectRequest.mutate(
      { approvalId: rejectTarget, reason: rejectReason },
      {
        onSuccess: () => {
          setRejectModalOpen(false);
          setRejectTarget(null);
          setRejectReason('');
        },
      },
    );
  };

  const pendingRows = pendingItems.map((item) => ({
    id: item.id,
    entityType: item.entityType,
    requestedBy: item.requestedBy,
    createdAt: item.createdAt,
  }));

  const historyRows = historyItems.map((item) => ({
    id: item.id,
    entityType: item.entityType,
    requestedBy: item.requestedBy,
    status: item.status,
    decidedBy: item.decidedBy ?? '—',
    decidedAt: item.decidedAt ?? '',
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-text-primary">
          Approval Queue
        </h1>
        {isCorporateAdmin && (
          <Link href="/admin/approval-rules">
            <Button kind="secondary" size="sm" renderIcon={Policy}>
              Approval Rules
            </Button>
          </Link>
        )}
      </div>

      <Tabs>
        <TabList aria-label="Approval tabs">
          <Tab>Pending ({pendingTotal})</Tab>
          <Tab>History</Tab>
        </TabList>
        <TabPanels>
          {/* Pending Tab */}
          <TabPanel>
            {pending.isError && (
              <InlineNotification
                kind="error"
                title="Failed to load pending approvals"
                hideCloseButton
              />
            )}

            <DataTable rows={pendingRows} headers={pendingHeaders} isSortable={false}>
              {({ rows: tableRows, headers: tableHeaders, getHeaderProps, getRowProps, getTableProps }) => (
                <TableContainer>
                  <Table {...getTableProps()}>
                    <TableHead>
                      <TableRow>
                        {tableHeaders.map((header) => {
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
                      {pending.isLoading ? (
                        <TableRow>
                          <TableCell colSpan={pendingHeaders.length}>
                            <div className="py-8 text-center text-text-secondary">
                              Loading...
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : pendingItems.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={pendingHeaders.length}>
                            <div className="py-8 text-center">
                              <Task size={48} className="mx-auto mb-4 text-text-secondary" />
                              <p className="text-lg font-medium text-text-primary">
                                No pending approvals
                              </p>
                              <p className="text-sm text-text-secondary mt-1">
                                All caught up!
                              </p>
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : (
                        tableRows.map((row) => {
                          const { key: rowKey, ...rowProps } = getRowProps({ row });
                          return (
                            <TableRow key={String(rowKey)} {...rowProps}>
                              {row.cells.map((cell) => {
                                if (cell.info.header === 'entityType') {
                                  return (
                                    <TableCell key={cell.id}>
                                      <Tag type="blue" size="sm">
                                        {requestTypeLabel(cell.value as string)}
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
                                        <Button
                                          kind="primary"
                                          size="sm"
                                          renderIcon={Checkmark}
                                          onClick={() => approveRequest.mutate(row.id)}
                                          disabled={approveRequest.isPending}
                                        >
                                          Approve
                                        </Button>
                                        <Button
                                          kind="danger--ghost"
                                          size="sm"
                                          renderIcon={Close}
                                          onClick={() => {
                                            setRejectTarget(row.id);
                                            setRejectReason('');
                                            setRejectModalOpen(true);
                                          }}
                                        >
                                          Reject
                                        </Button>
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

            {pendingTotal > pendingPerPage && (
              <Pagination
                page={pendingPage}
                pageSize={pendingPerPage}
                pageSizes={[10, 20, 50]}
                totalItems={pendingTotal}
                onChange={({ page: p, pageSize }: { page: number; pageSize: number }) => {
                  setPendingPage(p);
                  setPendingPerPage(pageSize);
                }}
              />
            )}
          </TabPanel>

          {/* History Tab */}
          <TabPanel>
            {history.isError && (
              <InlineNotification
                kind="error"
                title="Failed to load approval history"
                hideCloseButton
              />
            )}

            <DataTable rows={historyRows} headers={historyHeaders} isSortable={false}>
              {({ rows: tableRows, headers: tableHeaders, getHeaderProps, getRowProps, getTableProps }) => (
                <TableContainer>
                  <Table {...getTableProps()}>
                    <TableHead>
                      <TableRow>
                        {tableHeaders.map((header) => {
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
                      {history.isLoading ? (
                        <TableRow>
                          <TableCell colSpan={historyHeaders.length}>
                            <div className="py-8 text-center text-text-secondary">
                              Loading...
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : historyItems.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={historyHeaders.length}>
                            <div className="py-8 text-center text-text-secondary">
                              No approval history yet
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : (
                        tableRows.map((row) => {
                          const { key: rowKey, ...rowProps } = getRowProps({ row });
                          return (
                            <TableRow key={String(rowKey)} {...rowProps}>
                              {row.cells.map((cell) => {
                                if (cell.info.header === 'entityType') {
                                  return (
                                    <TableCell key={cell.id}>
                                      <Tag type="blue" size="sm">
                                        {requestTypeLabel(cell.value as string)}
                                      </Tag>
                                    </TableCell>
                                  );
                                }
                                if (cell.info.header === 'status') {
                                  return (
                                    <TableCell key={cell.id}>
                                      <StatusTag type={statusColor(cell.value as string)}>
                                        {cell.value as string}
                                      </StatusTag>
                                    </TableCell>
                                  );
                                }
                                if (cell.info.header === 'decidedAt') {
                                  return (
                                    <TableCell key={cell.id}>
                                      {(cell.value as string) ? formatDate(cell.value as string) : '—'}
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

            {historyTotal > historyPerPage && (
              <Pagination
                page={historyPage}
                pageSize={historyPerPage}
                pageSizes={[10, 20, 50]}
                totalItems={historyTotal}
                onChange={({ page: p, pageSize }: { page: number; pageSize: number }) => {
                  setHistoryPage(p);
                  setHistoryPerPage(pageSize);
                }}
              />
            )}
          </TabPanel>
        </TabPanels>
      </Tabs>

      {/* Reject Modal */}
      <Modal
        open={rejectModalOpen}
        modalHeading="Reject Request"
        primaryButtonText="Reject"
        secondaryButtonText="Cancel"
        danger
        onRequestSubmit={handleReject}
        onRequestClose={() => {
          setRejectModalOpen(false);
          setRejectTarget(null);
          setRejectReason('');
        }}
        primaryButtonDisabled={!rejectReason.trim() || rejectRequest.isPending}
      >
        <TextArea
          id="reject-reason"
          labelText="Reason for rejection"
          placeholder="Please provide a reason..."
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
      </Modal>
    </div>
  );
}
