/**
 * Public API client — no authentication required.
 * Used for /p/{slug} (public profile) and /v/{token} (public verification) pages.
 * AC-6: public routes, no credentials in fetch.
 * AC-8/AC-9: network error handling + plain text safety.
 */

import { ApiError, NetworkError, parseApiError } from "./errors";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 10_000;

/**
 * Fetch with timeout.
 * Automatically aborts after TIMEOUT_MS and throws NetworkError("timeout").
 */
async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
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
    if (error instanceof NetworkError) {
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
 * Parse response body based on status and content.
 * 200 → parse as JSON; 404/5xx → throw ApiError.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    const text = await response.text();
    try {
      return JSON.parse(text) as T;
    } catch {
      throw new Error("Invalid JSON from API");
    }
  }

  // Non-2xx — parse error body
  let body: unknown;
  try {
    const text = await response.text();
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }

  throw parseApiError(response.status, body);
}

/**
 * Get public profile by slug.
 * AC-1: display_name, verified_experiences.
 * AC-3: 404 "Kayıt bulunamadı".
 * AC-8: network error → NetworkError.
 */
export async function getPublicProfile(slug: string): Promise<{
  display_name: string;
  verified_experiences: Array<{
    id: string;
    organization_name_snapshot: string;
    role_snapshot: string;
    started_on_snapshot: string | null;
    ended_on_snapshot: string | null;
    claim_type: string;
    created_at: string;
  }>;
}> {
  try {
    const url = `${BASE_URL}/public/talents/${encodeURIComponent(slug)}`;
    const response = await fetchWithTimeout(url);
    return await handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError || error instanceof NetworkError) {
      throw error;
    }
    throw new NetworkError("network");
  }
}

/**
 * Get public verification by token.
 * AC-2: title, talent_name, organization, institution, attested_skills, verified_at.
 * AC-4: 404 "Kayıt bulunamadı".
 * AC-8: network error → NetworkError.
 */
export async function getPublicVerification(token: string): Promise<{
  title: string;
  talent_name: string;
  organization_name: string;
  organization_trust_level: string;
  organization_domain: string | null;
  institution_name: string | null;
  institution_trust_level: string | null;
  started_on: string | null;
  ended_on: string | null;
  verified_at: string;
  attested_skills: Array<{
    name_tr: string;
    claim_type: string;
    attestor_organization: string | null;
  }>;
}> {
  try {
    const url = `${BASE_URL}/public/v/${encodeURIComponent(token)}`;
    const response = await fetchWithTimeout(url);
    return await handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError || error instanceof NetworkError) {
      throw error;
    }
    throw new NetworkError("network");
  }
}
