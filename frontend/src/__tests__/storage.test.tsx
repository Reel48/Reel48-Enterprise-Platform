import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, act } from '@testing-library/react';

const mockFetchAuthSession = vi.fn();

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => mockFetchAuthSession(...args),
}));

vi.mock('next/image', () => ({
  default: (props: Record<string, unknown>) => {
    const { fill, unoptimized, ...rest } = props;
    return <img {...rest} />;
  },
}));

import { useFileUpload, useDownloadUrl } from '@/hooks/useStorage';
import { S3Image } from '@/components/ui/S3Image';

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

function mockAuthToken(token = 'test-id-token') {
  mockFetchAuthSession.mockResolvedValue({
    tokens: {
      idToken: { toString: () => token },
    },
  });
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('useFileUpload', () => {
  beforeEach(() => {
    mockAuthToken();
  });

  it('calls upload-url endpoint and PUTs file to S3', async () => {
    let capturedBody: Record<string, unknown> | null = null;
    let s3PutCalled = false;

    server.use(
      http.post('http://localhost:8000/api/v1/storage/upload-url', async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          data: {
            upload_url: 'https://s3.example.com/upload?signed=true',
            s3_key: 'company-123/brand-slug/products/abc.png',
            expires_in: 900,
          },
          meta: {},
          errors: [],
        });
      }),
      http.put('https://s3.example.com/upload', () => {
        s3PutCalled = true;
        return new HttpResponse(null, { status: 200 });
      }),
    );

    const { result } = renderHook(() => useFileUpload(), {
      wrapper: createWrapper(),
    });

    const file = new File(['image data'], 'test-photo.png', {
      type: 'image/png',
    });

    let s3Key: string | undefined;
    await act(async () => {
      s3Key = await result.current.mutateAsync({ file, category: 'products' });
    });

    expect(capturedBody).toEqual({
      category: 'products',
      content_type: 'image/png',
      file_extension: '.png',
    });
    expect(s3PutCalled).toBe(true);
    expect(s3Key).toBe('company-123/brand-slug/products/abc.png');
  });

  it('rejects files exceeding size limit before API call', async () => {
    const { result } = renderHook(() => useFileUpload(), {
      wrapper: createWrapper(),
    });

    // Create a file that exceeds the 5MB logo limit
    const largeContent = new Uint8Array(6 * 1024 * 1024);
    const file = new File([largeContent], 'huge-logo.png', {
      type: 'image/png',
    });

    await act(async () => {
      try {
        await result.current.mutateAsync({ file, category: 'logos' });
        expect.fail('Should have thrown');
      } catch (error) {
        expect((error as Error).message).toContain('exceeds maximum size');
        expect((error as Error).message).toContain('5MB');
      }
    });
  });

  it('throws when S3 upload fails', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/storage/upload-url', () => {
        return HttpResponse.json({
          data: {
            upload_url: 'https://s3.example.com/upload?signed=true',
            s3_key: 'company-123/brand-slug/products/abc.png',
            expires_in: 900,
          },
          meta: {},
          errors: [],
        });
      }),
      http.put('https://s3.example.com/upload', () => {
        return new HttpResponse(null, { status: 403 });
      }),
    );

    const { result } = renderHook(() => useFileUpload(), {
      wrapper: createWrapper(),
    });

    const file = new File(['data'], 'test.png', { type: 'image/png' });

    await act(async () => {
      try {
        await result.current.mutateAsync({ file, category: 'products' });
        expect.fail('Should have thrown');
      } catch (error) {
        expect((error as Error).message).toContain('Failed to upload');
      }
    });
  });
});

describe('useDownloadUrl', () => {
  beforeEach(() => {
    mockAuthToken();
  });

  it('calls download-url endpoint and returns the URL', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/storage/download-url', () => {
        return HttpResponse.json({
          data: {
            download_url: 'https://cdn.example.com/file.png?signed=true',
            expires_in: 3600,
          },
          meta: {},
          errors: [],
        });
      }),
    );

    const { result } = renderHook(() => useDownloadUrl(), {
      wrapper: createWrapper(),
    });

    let url: string | undefined;
    await act(async () => {
      url = await result.current.mutateAsync('company-123/brand-slug/products/abc.png');
    });

    expect(url).toBe('https://cdn.example.com/file.png?signed=true');
  });
});

describe('S3Image', () => {
  beforeEach(() => {
    mockAuthToken();
  });

  it('shows fallback when s3Key is null', () => {
    render(
      <S3Image s3Key={null} alt="test" width={100} height={100} />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId('s3-image-placeholder')).toBeInTheDocument();
    expect(screen.getByText('No image')).toBeInTheDocument();
  });

  it('shows custom fallback when s3Key is null', () => {
    render(
      <S3Image
        s3Key={null}
        alt="test"
        width={100}
        height={100}
        fallback={<div data-testid="custom-fallback">Custom</div>}
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
  });

  it('shows loading state while resolving URL', () => {
    // Don't set up MSW handler — the request will hang, showing loading state
    server.use(
      http.post('http://localhost:8000/api/v1/storage/download-url', () => {
        return new Promise(() => {
          // Never resolves — simulates pending request
        });
      }),
    );

    render(
      <S3Image
        s3Key="company-123/brand-slug/products/abc.png"
        alt="test"
        width={100}
        height={100}
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId('s3-image-loading')).toBeInTheDocument();
  });

  it('renders image after URL resolves', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/storage/download-url', () => {
        return HttpResponse.json({
          data: {
            download_url: 'https://cdn.example.com/image.png',
            expires_in: 3600,
          },
          meta: {},
          errors: [],
        });
      }),
    );

    render(
      <S3Image
        s3Key="company-123/brand-slug/products/abc.png"
        alt="Product image"
        width={200}
        height={200}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      const img = screen.getByAltText('Product image');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'https://cdn.example.com/image.png');
    });
  });

  it('shows fallback on download URL error', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/storage/download-url', () => {
        return HttpResponse.json(
          {
            data: null,
            errors: [{ code: 'FORBIDDEN', message: 'Access denied' }],
          },
          { status: 403 },
        );
      }),
    );

    render(
      <S3Image
        s3Key="other-company/brand/products/abc.png"
        alt="test"
        width={100}
        height={100}
      />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId('s3-image-placeholder')).toBeInTheDocument();
    });
  });
});
