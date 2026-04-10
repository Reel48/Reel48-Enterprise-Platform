'use client';

import { useMutation } from '@tanstack/react-query';

import { api } from '@/lib/api/client';
import type {
  DownloadUrlResponse,
  StorageCategory,
  UploadUrlResponse,
} from '@/types/storage';

const MAX_FILE_SIZES: Record<StorageCategory, number> = {
  logos: 5 * 1024 * 1024,
  products: 10 * 1024 * 1024,
  catalog: 25 * 1024 * 1024,
  profiles: 5 * 1024 * 1024,
};

/**
 * Request a pre-signed upload URL, then PUT the file directly to S3.
 * Returns the s3_key on success (to store in the database).
 */
export function useFileUpload() {
  return useMutation({
    mutationFn: async ({
      file,
      category,
    }: {
      file: File;
      category: StorageCategory;
    }) => {
      // 1. Client-side file size validation
      const maxSize = MAX_FILE_SIZES[category];
      if (file.size > maxSize) {
        throw new Error(
          `File exceeds maximum size of ${Math.round(maxSize / (1024 * 1024))}MB for ${category}`,
        );
      }

      // 2. Get pre-signed URL from backend
      const extension = '.' + (file.name.split('.').pop()?.toLowerCase() ?? '');
      const res = await api.post<UploadUrlResponse>(
        '/api/v1/storage/upload-url',
        {
          category,
          contentType: file.type,
          fileExtension: extension,
        },
      );

      // 3. Upload directly to S3
      const uploadResponse = await fetch(res.data.uploadUrl, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type },
      });

      if (!uploadResponse.ok) {
        throw new Error('Failed to upload file to S3');
      }

      return res.data.s3Key;
    },
  });
}

/**
 * Get a pre-signed download URL for an s3_key.
 */
export function useDownloadUrl() {
  return useMutation({
    mutationFn: async (s3Key: string) => {
      const res = await api.post<DownloadUrlResponse>(
        '/api/v1/storage/download-url',
        { s3Key },
      );
      return res.data.downloadUrl;
    },
  });
}
