export interface PaginationMeta {
  page: number;
  perPage: number;
  total: number;
}

export interface ApiError {
  code: string;
  message: string;
  field?: string | null;
}

export interface ApiResponse<T> {
  data: T;
  meta: Record<string, unknown>;
  errors: ApiError[];
}

export interface ApiListResponse<T> {
  data: T[];
  meta: PaginationMeta;
  errors: ApiError[];
}
