/**
 * PLAN 3.6 — Admin ekranları API client (kurum doğrulama + skill yönetimi).
 * Endpoints: GET /admin/verification-queue, POST /admin/organizations/{id}/verification-level,
 * POST/PATCH/DELETE /admin/skills*
 * Returns response or throws ApiError/NetworkError.
 */

import { apiFetch } from "./client";

// ============================================================================
// Type definitions
// ============================================================================

export interface Organization {
  id: string;
  name: string;
  legal_id?: string | null;
  domain?: string | null;
  verification_level: string; // "T1" | "T2" | "T3" | "T4"
  verified_at?: string | null;
  created_at: string;
}

/** Pagination envelope shared by the three admin list endpoints. */
export interface PagedResponse<T> {
  items: T[];
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PageParams {
  limit?: number;
  offset?: number;
}

export const ADMIN_PAGE_SIZE = 50;
export const ADMIN_MAX_PAGE_SIZE = 200;

function pageQuery({ limit = ADMIN_PAGE_SIZE, offset = 0 }: PageParams = {}): string {
  return `?limit=${limit}&offset=${offset}`;
}

export type VerificationQueueResponse = PagedResponse<Organization>;

export interface Skill {
  id: string;
  slug: string;
  name_tr: string;
  name_en?: string | null;
  category: "LANGUAGE" | "FRAMEWORK" | "TOOL" | "DOMAIN" | "SOFT";
  parent_id?: string | null;
  status: string; // "ACTIVE" | "DEPRECATED" | "MERGED"
  merged_into_id?: string | null;
}

export type SkillsListResponse = PagedResponse<Skill>;

// ============================================================================
// API functions
// ============================================================================

/**
 * Fetch verification queue (organizations pending verification level decision).
 * GET /admin/verification-queue
 * AC-1: Happy path — returns items[]
 * AC-4: Empty queue — returns items: []
 * AC-8: 500/timeout — throws ApiError/NetworkError
 * AC-9/AC-S2: Unauthorized — throws ApiError(404)
 */
export async function getVerificationQueue(
  params?: PageParams
): Promise<VerificationQueueResponse | undefined> {
  return (await apiFetch<VerificationQueueResponse>(
    `/admin/verification-queue${pageQuery(params)}`
  )) as VerificationQueueResponse | undefined;
}

/**
 * Update organization verification level.
 * POST /admin/organizations/{id}/verification-level
 * AC-2: Happy path — returns updated Organization
 * AC-3: Resource not found — throws ApiError(404, "Kurum bulunamadı.")
 * AC-8: 500/timeout — throws ApiError/NetworkError
 * AC-9/AC-S2: Unauthorized — throws ApiError(404)
 */
export async function updateVerificationLevel(
  organizationId: string,
  verificationLevel: string
): Promise<Organization | undefined> {
  return (await apiFetch<Organization>(
    `/admin/organizations/${organizationId}/verification-level`,
    {
      method: "POST",
      body: { verification_level: verificationLevel },
    }
  )) as Organization | undefined;
}

/**
 * Reject a pending verification application (org leaves the queue, level unchanged).
 * POST /admin/organizations/{id}/verification-reject
 */
export async function rejectVerification(organizationId: string): Promise<Organization | undefined> {
  return (await apiFetch<Organization>(
    `/admin/organizations/${organizationId}/verification-reject`,
    {
      method: "POST",
      body: {},
    }
  )) as Organization | undefined;
}

/**
 * Create a new skill.
 * POST /admin/skills
 * AC-5: Happy path — returns new Skill
 * AC-6: Slug conflict — throws ApiError(409, "Bu slug zaten kullanımda.")
 * AC-8: 500/timeout — throws ApiError/NetworkError
 * AC-9/AC-S2: Unauthorized — throws ApiError(404)
 */
export async function createSkill(
  slug: string,
  name_tr: string,
  category: string,
  name_en?: string
): Promise<Skill | undefined> {
  return (await apiFetch<Skill>("/admin/skills", {
    method: "POST",
    body: { slug, name_tr, name_en, category },
  })) as Skill | undefined;
}

/**
 * Update an existing skill.
 * PATCH /admin/skills/{id}
 * AC-7: Happy path — returns updated Skill
 * AC-8: 500/timeout — throws ApiError/NetworkError
 * AC-9/AC-S2: Unauthorized — throws ApiError(404)
 */
export async function updateSkill(
  skillId: string,
  name_tr: string
): Promise<Skill | undefined> {
  return (await apiFetch<Skill>(`/admin/skills/${skillId}`, {
    method: "PATCH",
    body: { name_tr },
  })) as Skill | undefined;
}

/**
 * Deprecate a skill.
 * POST /admin/skills/{id}/deprecate
 * AC-7: Happy path — returns Skill with status DEPRECATED
 * AC-8: 500/timeout — throws ApiError/NetworkError
 * AC-9/AC-S2: Unauthorized — throws ApiError(404)
 */
export async function deprecateSkill(skillId: string): Promise<Skill | undefined> {
  return (await apiFetch<Skill>(`/admin/skills/${skillId}/deprecate`, {
    method: "POST",
  })) as Skill | undefined;
}

/**
 * Merge a skill into another.
 * POST /admin/skills/{id}/merge
 * AC-7: Happy path — returns Skill with status MERGED and merged_into_id set
 * AC-8: 500/timeout — throws ApiError/NetworkError
 * AC-9/AC-S2: Unauthorized — throws ApiError(404)
 */
export async function mergeSkill(
  skillId: string,
  targetId: string
): Promise<Skill | undefined> {
  return (await apiFetch<Skill>(`/admin/skills/${skillId}/merge`, {
    method: "POST",
    body: { merged_into_id: targetId },
  })) as Skill | undefined;
}

/**
 * Fetch all skills (for admin skill taxonomy management).
 * GET /admin/skills
 * AC-5: Happy path — returns items[]
 * AC-8: 500/timeout — throws ApiError/NetworkError
 * AC-9/AC-S2: Unauthorized — throws ApiError(404)
 */
export async function getSkills(params?: PageParams): Promise<SkillsListResponse | undefined> {
  return (await apiFetch<SkillsListResponse>(
    `/admin/skills${pageQuery(params)}`
  )) as SkillsListResponse | undefined;
}

/**
 * Walk every page of GET /admin/skills (limit 200) until has_more is false.
 * Used by the merge dialog so the target list is never limited to the visible page.
 * A failing page rejects the whole call — a partial target list is never returned.
 */
export async function getAllSkills(): Promise<Skill[]> {
  const all: Skill[] = [];
  let offset = 0;
  for (;;) {
    const page = await getSkills({ limit: ADMIN_MAX_PAGE_SIZE, offset });
    if (!page) break;
    all.push(...page.items);
    if (!page.has_more || page.items.length === 0) break;
    offset += page.items.length;
  }
  return all;
}

// ============================================================================
// Fraud flag kuyruğu (PLAN 3.54) — AI işaretler, admin karar verir
// ============================================================================

export interface FraudFlag {
  id: string;
  subject_type: "ATTESTATION" | "ORGANIZATION" | "INSTITUTION";
  subject_id: string;
  /** PLAN 3.56: kuruluş/kurum adı; tanıklık işaretlerinde null. */
  subject_label: string | null;
  /** PLAN 3.56: işareti üreten kural/kontrol kodu; 3.54 tanıklık metni işaretlerinde null. */
  signal: string | null;
  reason: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  model: string;
  created_at: string;
}

export type FraudQueueResponse = PagedResponse<FraudFlag>;

/**
 * Fetch pending fraud flags.
 * GET /admin/fraud-queue
 */
export async function getFraudQueue(params?: PageParams): Promise<FraudQueueResponse | undefined> {
  return (await apiFetch<FraudQueueResponse>(
    `/admin/fraud-queue${pageQuery(params)}`
  )) as FraudQueueResponse | undefined;
}

/**
 * Record the admin's decision on a flag — CONFIRMED (real fraud) or DISMISSED (false positive).
 * POST /admin/fraud-queue/{id}/resolve
 */
export async function resolveFraudFlag(
  flagId: string,
  outcome: "CONFIRMED" | "DISMISSED"
): Promise<FraudFlag | undefined> {
  return (await apiFetch<FraudFlag>(`/admin/fraud-queue/${flagId}/resolve`, {
    method: "POST",
    body: { outcome },
  })) as FraudFlag | undefined;
}
