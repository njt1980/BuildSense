const DEFAULT_API_BASE_URL = "http://localhost:8001";

/**
 * Returns the configured backend API base URL with whitespace and trailing
 * slashes removed so fetch calls cannot produce malformed URLs.
 */
export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL)
    .trim()
    .replace(/\/+$/, "");
}
