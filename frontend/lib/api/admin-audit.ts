/**
 * Admin audit log (A1) and reviewed fraud-flag history (F2) API client.
 * Endpoints: GET /admin/audit-events, GET /admin/fraud-flags/history
 * Returns response or throws ApiError/NetworkError (see ./client).
 */

import { apiFetch } from "./client";

export const AUDIT_PAGE_SIZE = 50;

export interface PagedResponse<T> {
  items: T[];
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface AuditEvent {
  id: number;
  actor_user_id?: string | null;
  actor_ip?: string | null;
  action: string;
  subject_type: string;
  subject_id?: string | null;
  result: string;
  metadata?: Record<string, string | number | boolean | null> | null;
  created_at: string;
}

export type AuditEventsResponse = PagedResponse<AuditEvent>;

export interface AuditEventsParams {
  action?: string;
  subject_type?: string;
  actor_user_id?: string;
  limit?: number;
  offset?: number;
}

export interface FraudHistoryItem {
  id: string;
  subject_type: string;
  subject_id: string;
  subject_label?: string | null;
  signal?: string | null;
  reason: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  model: string;
  status: "CONFIRMED" | "DISMISSED";
  created_at: string;
  reviewed_at?: string | null;
  reviewed_by_user_id?: string | null;
}

export type FraudHistoryResponse = PagedResponse<FraudHistoryItem>;

export interface FraudHistoryParams {
  status?: "CONFIRMED" | "DISMISSED";
  limit?: number;
  offset?: number;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

/** GET /admin/audit-events — newest first, filtered and paged server-side. */
export async function getAuditEvents(
  params: AuditEventsParams = {}
): Promise<AuditEventsResponse | undefined> {
  const { limit = AUDIT_PAGE_SIZE, offset = 0, ...filters } = params;
  return (await apiFetch<AuditEventsResponse>(
    `/admin/audit-events${buildQuery({ ...filters, limit, offset })}`
  )) as AuditEventsResponse | undefined;
}

/** GET /admin/fraud-flags/history — reviewed (CONFIRMED/DISMISSED) flags, newest review first. */
export async function getFraudHistory(
  params: FraudHistoryParams = {}
): Promise<FraudHistoryResponse | undefined> {
  const { limit = AUDIT_PAGE_SIZE, offset = 0, status } = params;
  return (await apiFetch<FraudHistoryResponse>(
    `/admin/fraud-flags/history${buildQuery({ status, limit, offset })}`
  )) as FraudHistoryResponse | undefined;
}
