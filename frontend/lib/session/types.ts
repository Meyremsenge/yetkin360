/**
 * AC-7: Type-safe /me response.
 * Hand-written: /me has no OpenAPI schema yet (PLAN 1.7).
 * Replace with generated types when it does — see .claude/rules/frontend.md.
 *
 * Required: user (id string), organizations[], institutions[]
 * Optional: talent_profile (object | null), user.email, user.full_name
 *
 * AC-1/AC-2: talent_profile strengthened with concrete fields (all optional).
 * Backward compatible: still accepts Record<string, unknown> | null via union.
 */

export interface TalentProfile {
  id?: string;
  institution_id?: string | null;
  headline?: string | null;
  department?: string | null;
  study_year?: number | null;
  city?: string | null;
  visibility?: string | null;
  public_slug?: string | null;
  [key: string]: unknown; // Allow unknown fields for extensibility
}

/** The caller's own membership in an organization (SPRINT A: role and unit added). */
export interface OrganizationRef {
  id: string;
  name: string;
  role: "ADMIN" | "MEMBER";
  unit: string | null;
}

/** The caller's own membership in an institution (SPRINT A: role added). */
export interface InstitutionRef {
  id: string;
  name: string;
  role: "ADMIN" | "COORDINATOR" | "SUPERVISOR";
}

export interface MeResponse {
  user: {
    id: string;
    email?: string;
    full_name?: string;
    email_verified?: boolean;
    is_platform_admin?: boolean;
  };
  talent_profile?: TalentProfile | null;
  organizations: OrganizationRef[];
  institutions: InstitutionRef[];
}

export function isMeResponse(value: unknown): value is MeResponse {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const obj = value as Record<string, unknown>;

  // Check user
  if (typeof obj.user !== "object" || obj.user === null || Array.isArray(obj.user)) {
    return false;
  }

  const user = obj.user as Record<string, unknown>;
  if (typeof user.id !== "string") {
    return false;
  }

  // Optional user fields are allowed to be any type or missing
  // email and full_name are optional, no strict type check needed

  // Check talent_profile (optional)
  if ("talent_profile" in obj) {
    const tp = obj.talent_profile;
    if (tp !== null && tp !== undefined && typeof tp !== "object") {
      return false;
    }
    if (Array.isArray(tp)) {
      return false;
    }
  }

  // Check organizations (required, must be array)
  if (!Array.isArray(obj.organizations)) {
    return false;
  }

  // Check institutions (required, must be array)
  if (!Array.isArray(obj.institutions)) {
    return false;
  }

  return true;
}
