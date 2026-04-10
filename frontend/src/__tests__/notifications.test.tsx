import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  usePathname: () => '/notifications',
}));

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
vi.mock('@/lib/api/client', () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn(),
  },
}));

import NotificationsPage from '@/app/(authenticated)/notifications/page';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

const mockNotifications = [
  {
    id: 'n-1',
    title: 'New catalog available',
    notificationType: 'catalog_available',
    isRead: false,
    createdAt: '2026-04-01T10:00:00Z',
    linkUrl: '/catalog/cat-1',
  },
  {
    id: 'n-2',
    title: 'Order shipped',
    notificationType: 'order_update',
    isRead: true,
    createdAt: '2026-03-30T14:00:00Z',
    linkUrl: '/orders/ord-1',
  },
  {
    id: 'n-3',
    title: 'Company announcement',
    notificationType: 'announcement',
    isRead: false,
    createdAt: '2026-03-29T08:00:00Z',
    linkUrl: null,
  },
];

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders notification feed with items', async () => {
    mockApiGet.mockResolvedValue({
      data: mockNotifications,
      meta: { page: 1, perPage: 20, total: 3, unreadCount: 2 },
      errors: [],
    });

    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('New catalog available')).toBeInTheDocument();
    });

    expect(screen.getByText('Order shipped')).toBeInTheDocument();
    expect(screen.getByText('Company announcement')).toBeInTheDocument();
  });

  it('shows unread count in header', async () => {
    mockApiGet.mockResolvedValue({
      data: mockNotifications,
      meta: { page: 1, perPage: 20, total: 3, unreadCount: 2 },
      errors: [],
    });

    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('2 unread')).toBeInTheDocument();
    });
  });

  it('shows empty state when no notifications', async () => {
    mockApiGet.mockResolvedValue({
      data: [],
      meta: { page: 1, perPage: 20, total: 0, unreadCount: 0 },
      errors: [],
    });

    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('No notifications yet')).toBeInTheDocument();
    });
  });

  it('shows unread empty state when filter is active', async () => {
    // First call (unreadOnly=false) returns notifications
    mockApiGet
      .mockResolvedValueOnce({
        data: mockNotifications,
        meta: { page: 1, perPage: 20, total: 3, unreadCount: 2 },
        errors: [],
      })
      // Second call (after toggle, unreadOnly=true) returns empty
      .mockResolvedValueOnce({
        data: [],
        meta: { page: 1, perPage: 20, total: 0, unreadCount: 0 },
        errors: [],
      });

    const user = userEvent.setup();
    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('New catalog available')).toBeInTheDocument();
    });

    // Toggle the unread filter
    const toggle = screen.getByRole('switch');
    await user.click(toggle);

    await waitFor(() => {
      expect(screen.getByText('No unread notifications')).toBeInTheDocument();
    });
  });

  it('shows Mark all read button when there are unread notifications', async () => {
    mockApiGet.mockResolvedValue({
      data: mockNotifications,
      meta: { page: 1, perPage: 20, total: 3, unreadCount: 2 },
      errors: [],
    });

    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Mark all read')).toBeInTheDocument();
    });
  });

  it('does not show Mark all read when unread count is 0', async () => {
    const allRead = mockNotifications.map((n) => ({ ...n, isRead: true }));
    mockApiGet.mockResolvedValue({
      data: allRead,
      meta: { page: 1, perPage: 20, total: 3, unreadCount: 0 },
      errors: [],
    });

    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Order shipped')).toBeInTheDocument();
    });

    expect(screen.queryByText('Mark all read')).not.toBeInTheDocument();
  });

  it('renders notification type tags correctly', async () => {
    mockApiGet.mockResolvedValue({
      data: mockNotifications,
      meta: { page: 1, perPage: 20, total: 3, unreadCount: 2 },
      errors: [],
    });

    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Catalog')).toBeInTheDocument();
    });

    expect(screen.getByText('Order')).toBeInTheDocument();
    expect(screen.getByText('Announcement')).toBeInTheDocument();
  });

  it('marks notification as read and navigates on click', async () => {
    mockApiGet.mockResolvedValue({
      data: mockNotifications,
      meta: { page: 1, perPage: 20, total: 3, unreadCount: 2 },
      errors: [],
    });
    mockApiPost.mockResolvedValue({ data: {}, meta: {}, errors: [] });

    const user = userEvent.setup();
    render(<NotificationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('New catalog available')).toBeInTheDocument();
    });

    // Click the first (unread) notification
    await user.click(screen.getByText('New catalog available'));

    // Should call mark-as-read API
    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith('/api/v1/notifications/n-1/read');
    });

    // Should navigate to link URL
    expect(mockPush).toHaveBeenCalledWith('/catalog/cat-1');
  });

  it('shows page heading', async () => {
    mockApiGet.mockResolvedValue({
      data: [],
      meta: { page: 1, perPage: 20, total: 0, unreadCount: 0 },
      errors: [],
    });

    render(<NotificationsPage />, { wrapper: createWrapper() });

    expect(screen.getByText('Notifications')).toBeInTheDocument();
  });
});
