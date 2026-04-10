export interface UploadUrlRequest {
  category: 'logos' | 'products' | 'catalog' | 'profiles';
  contentType: string;
  fileExtension: string;
}

export interface UploadUrlResponse {
  uploadUrl: string;
  s3Key: string;
  expiresIn: number;
}

export interface DownloadUrlResponse {
  downloadUrl: string;
  expiresIn: number;
}

export type StorageCategory = UploadUrlRequest['category'];
