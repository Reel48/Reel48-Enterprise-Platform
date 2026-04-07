/**
 * Converts a snake_case string to camelCase.
 * Example: "company_id" -> "companyId"
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z0-9])/g, (_, char) => char.toUpperCase());
}

/**
 * Converts a camelCase string to snake_case.
 * Example: "companyId" -> "company_id"
 */
export function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (char) => `_${char.toLowerCase()}`);
}

/**
 * Recursively transforms all keys in an object or array using the given
 * transform function. Handles nested objects, arrays, null, and primitives.
 */
export function deepTransformKeys<T>(
  data: unknown,
  transformFn: (key: string) => string,
): T {
  if (data === null || data === undefined) {
    return data as T;
  }

  if (Array.isArray(data)) {
    return data.map((item) => deepTransformKeys(item, transformFn)) as T;
  }

  if (data instanceof Date) {
    return data as T;
  }

  if (typeof data === 'object') {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data)) {
      result[transformFn(key)] = deepTransformKeys(value, transformFn);
    }
    return result as T;
  }

  return data as T;
}
