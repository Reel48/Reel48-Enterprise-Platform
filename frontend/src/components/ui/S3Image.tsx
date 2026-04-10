'use client';

import { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { Loading } from '@carbon/react';

import { useDownloadUrl } from '@/hooks/useStorage';

interface S3ImageProps {
  s3Key: string | null;
  alt: string;
  width: number;
  height: number;
  fallback?: React.ReactNode;
  className?: string;
}

/**
 * Displays an image stored in S3 by resolving a pre-signed download URL.
 * Shows a loading state while the URL is being fetched, and a fallback
 * if s3Key is null or the fetch fails.
 */
export function S3Image({
  s3Key,
  alt,
  width,
  height,
  fallback,
  className,
}: S3ImageProps) {
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(null);
  const [prevKey, setPrevKey] = useState<string | null>(null);
  const downloadUrl = useDownloadUrl();

  const resolve = useCallback(
    (key: string) => {
      downloadUrl.mutate(key, {
        onSuccess: (url) => setResolvedUrl(url),
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  useEffect(() => {
    if (s3Key && s3Key !== prevKey) {
      setPrevKey(s3Key);
      setResolvedUrl(null);
      resolve(s3Key);
    }
  }, [s3Key, prevKey, resolve]);

  // No s3Key provided — show fallback
  if (!s3Key) {
    return (
      <>{fallback ?? <DefaultPlaceholder width={width} height={height} />}</>
    );
  }

  // Loading state
  if (downloadUrl.isPending || (!resolvedUrl && !downloadUrl.isError)) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ width, height }}
        data-testid="s3-image-loading"
      >
        <Loading withOverlay={false} small />
      </div>
    );
  }

  // Error state — show fallback
  if (downloadUrl.isError || !resolvedUrl) {
    return (
      <>{fallback ?? <DefaultPlaceholder width={width} height={height} />}</>
    );
  }

  return (
    <Image
      src={resolvedUrl}
      alt={alt}
      width={width}
      height={height}
      className={className}
      unoptimized
    />
  );
}

function DefaultPlaceholder({
  width,
  height,
}: {
  width: number;
  height: number;
}) {
  return (
    <div
      className="flex items-center justify-center bg-gray-100 text-gray-400"
      style={{ width, height }}
      data-testid="s3-image-placeholder"
    >
      No image
    </div>
  );
}
