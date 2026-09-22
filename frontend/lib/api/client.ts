/**
 * AC-3/AC-4/AC-5: API client with single-flight 401→refresh→retry logic.
 * AC-S2: credentials:"include", X-CSRF-Token header (no JWT decode, no token in JS storage).
 * AC-S6: Concurrent 401s share single refresh promise.
 * AC-10: 401 EMAIL_NOT_VERIFIED → no refresh.
 * AC-5: 10s timeout; no automatic retry in apiFetch (TanStack Query handles GET retry).
 */

import {
  ApiError,
  NetworkError,
  SessionExpiredError,
  InvalidResponseError,
  parseApiError,
} from "./errors";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const TIMEOUT_MS = 10_000;

// Single in-flight refresh promise (module-level state)
let refreshPromise: Promise<void> | null = null;

/**
 * Extract csrf_token from document.cookie.
 */
function getCsrfToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/csrf_token=([^;]*)/);
  return match?.[1] || "";
}

export interface FetchInit {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

/**
 * Parse response body based on status and content.
 * 204 → undefined; otherwise parse as JSON or undefined if empty.
 */
async function readBody<T>(response: Response): Promise<T | undefined> {
  if (response.status === 204) {
    return undefined;
  }

  const text = await response.text();
  if (!text) {
    return undefined;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new InvalidResponseError(
      "Sunucudan geçersiz yanıt alındı"
    );
  }
}

/**
 * Fetch with timeout.
 * Automatically aborts after TIMEOUT_MS and throws NetworkError("timeout").
 */
async function fetchWithTimeout(
  url: string,
  init: RequestInit
): Promise<Response> {
  const controller = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | undefined;

  try {
    return await Promise.race([
      fetch(url, { ...init, signal: controller.signal }),
      new Promise<never>((_resolve, reject) => {
        timeoutId = setTimeout(() => {
          controller.abort();
          reject(new NetworkError("timeout"));
        }, TIMEOUT_MS);
      }),
    ]);
  } catch (error) {
    if (error instanceof NetworkError && error.kind === "timeout") {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new NetworkError("timeout");
    }
    throw new NetworkError("network");
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Handle response: parse body and return result.
 * Throws ApiError, SessionExpiredError, or InvalidResponseError as appropriate.
 */
async function handleResponse<T>(response: Response): Promise<T | undefined> {
  if (response.ok) {
    return readBody<T>(response);
  }

  // Non-2xx
  let body: unknown;
  try {
    const text = await response.text();
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }

  throw parseApiError(response.status, body);
}

export async function apiFetch<T = unknown>(
  path: string,
  init?: FetchInit
): Promise<T | undefined> {
  const url = `${BASE_URL}${path}`;
  const method = init?.method;

  // Build request headers
  const requestHeaders: Record<string, string> = {
    "content-type": "application/json",
    ...(init?.headers || {}),
  };

  // Add X-CSRF-Token for mutating methods
  if (method && ["POST", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      requestHeaders["x-csrf-token"] = csrfToken;
    }
  }

  // Build fetch options
  const fetchOptions: RequestInit = {
    method,
    credentials: "include",
    headers: requestHeaders,
  };

  // Add body for mutations
  if (init?.body !== undefined) {
    fetchOptions.body = JSON.stringify(init.body);
  }

  return performFetchWithRefresh<T>(url, fetchOptions);
}

async function performFetchWithRefresh<T>(
  url: string,
  options: RequestInit
): Promise<T | undefined> {
  try {
    const response = await fetchWithTimeout(url, options);
    const result = await handleResponse<T>(response);
    return result;
  } catch (error) {
    // 401 UNAUTHENTICATED → attempt refresh
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      error.code === "UNAUTHENTICATED"
    ) {
      await performRefresh();

      // Retry original request exactly once
      const retryResponse = await fetchWithTimeout(url, options);
      if (retryResponse.status === 401) {
        throw new SessionExpiredError();
      }
      return handleResponse<T>(retryResponse);
    }

    if (
      error instanceof ApiError ||
      error instanceof SessionExpiredError ||
      error instanceof InvalidResponseError ||
      error instanceof NetworkError
    ) {
      throw error;
    }

    throw new NetworkError("network");
  }
}

async function performRefresh(): Promise<void> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const headers: Record<string, string> = {};
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        headers["x-csrf-token"] = csrfToken;
      }

      const response = await fetchWithTimeout(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers,
      });

      if (!response.ok) {
        // Non-2xx refresh response
        let body: unknown;
        try {
          const text = await response.text();
          body = text ? JSON.parse(text) : null;
        } catch {
          body = null;
        }

        if (response.status === 401) {
          throw new SessionExpiredError();
        }

        // 429, 5xx, etc. → ApiError
        throw parseApiError(response.status, body);
      }
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}
