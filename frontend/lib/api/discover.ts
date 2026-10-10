/**
 * PLAN R.1 — Keşfet dizini API katmanı. Sözleşme: backend/app/api/discover.py,
 * tasarım: docs/kesfet-tasarim.md.
 *
 * Bir dizin/arama, eşleştirme değil: yanıtta puan yok, sıra sunucuda sabit.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export const DISCOVER_MIN_QUERY_LENGTH = 2;
export const DISCOVER_MAX_SKILL_FILTERS = 5;

export interface DiscoverTalent {
  public_slug: string;
  full_name: string;
  headline: string | null;
  department: string | null;
  city: string | null;
  institution_name: string | null;
  sealed_skills: string[];
  verified_experience_count: number;
}

export interface DiscoverOrganization {
  id: string;
  name: string;
  verification_level: string;
  domain: string | null;
}

export interface DiscoverPage<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface DiscoverTalentFilters {
  q?: string;
  skillIds?: string[];
  department?: string;
  city?: string;
  cursor?: string | null;
}

export interface DiscoverOrganizationFilters {
  q?: string;
  cursor?: string | null;
}

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

/** Backend rejects q shorter than 2 chars with 422; a shorter term is "no search yet". */
function appendQuery(params: URLSearchParams, q: string | undefined) {
  const term = q?.trim() ?? "";
  if (term.length >= DISCOVER_MIN_QUERY_LENGTH) params.set("q", term);
}

function withQuery(path: string, params: URLSearchParams): string {
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export async function listDiscoverTalents(
  filters: DiscoverTalentFilters = {}
): Promise<DiscoverPage<DiscoverTalent>> {
  const params = new URLSearchParams();
  appendQuery(params, filters.q);
  for (const skillId of filters.skillIds ?? []) params.append("skill_id", skillId);
  if (filters.department?.trim()) params.set("department", filters.department.trim());
  if (filters.city?.trim()) params.set("city", filters.city.trim());
  if (filters.cursor) params.set("cursor", filters.cursor);

  const response = await apiFetch<DiscoverPage<DiscoverTalent>>(withQuery("/discover/talents", params));
  if (!response) throw unexpectedResponse();
  return response;
}

export async function listDiscoverOrganizations(
  filters: DiscoverOrganizationFilters = {}
): Promise<DiscoverPage<DiscoverOrganization>> {
  const params = new URLSearchParams();
  appendQuery(params, filters.q);
  if (filters.cursor) params.set("cursor", filters.cursor);

  const response = await apiFetch<DiscoverPage<DiscoverOrganization>>(
    withQuery("/discover/organizations", params)
  );
  if (!response) throw unexpectedResponse();
  return response;
}
