/**
 * Admin directory API client (U1, U2, O1, O4, I1): users, organizations, institutions.
 * All endpoints are platform-admin only; non-admins get 404 from the server.
 */

import { apiFetch } from "./client";

export interface Page<T> {
  items: T[];
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface AdminUser {
  id: string;
  email: string;
  status: "PENDING" | "ACTIVE" | "SUSPENDED" | "DELETED";
  is_platform_admin: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface AdminOrganization {
  id: string;
  name: string;
  legal_id: string | null;
  domain: string | null;
  verification_level: string;
  verified_at: string | null;
  status: string;
  created_at: string;
}

export interface AdminInstitution {
  id: string;
  name: string;
  domain: string | null;
  verification_level: string;
  status: string;
  created_at: string;
}

export type VerificationLevel = "T1" | "T2" | "T3" | "T4";
export type DirectoryKind = "users" | "organizations" | "institutions";

export interface ListParams {
  q?: string;
  status?: string;
  verification_level?: string;
  limit?: number;
  offset?: number;
}

export const PAGE_SIZE = 50;

function query(params: ListParams): string {
  const search = new URLSearchParams();
  const q = params.q?.trim();
  if (q) search.set("q", q);
  if (params.status) search.set("status", params.status);
  if (params.verification_level) search.set("verification_level", params.verification_level);
  search.set("limit", String(params.limit ?? PAGE_SIZE));
  search.set("offset", String(params.offset ?? 0));
  return search.toString();
}

async function list<T>(kind: DirectoryKind, params: ListParams): Promise<Page<T> | undefined> {
  return (await apiFetch<Page<T>>(`/admin/${kind}?${query(params)}`)) as Page<T> | undefined;
}

export const listUsers = (params: ListParams = {}) => list<AdminUser>("users", params);
export const listOrganizations = (params: ListParams = {}) => list<AdminOrganization>("organizations", params);
export const listInstitutions = (params: ListParams = {}) => list<AdminInstitution>("institutions", params);

/** POST /admin/{kind}/{id}/suspend | reactivate — idempotent on the server. */
export async function setSuspended<T>(kind: DirectoryKind, id: string, suspended: boolean): Promise<T | undefined> {
  const action = suspended ? "suspend" : "reactivate";
  return (await apiFetch<T>(`/admin/${kind}/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
    body: {},
  })) as T | undefined;
}

export async function setInstitutionVerificationLevel(
  id: string,
  verificationLevel: VerificationLevel
): Promise<AdminInstitution | undefined> {
  return (await apiFetch<AdminInstitution>(
    `/admin/institutions/${encodeURIComponent(id)}/verification-level`,
    { method: "POST", body: { verification_level: verificationLevel } }
  )) as AdminInstitution | undefined;
}
