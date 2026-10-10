import { apiFetch } from "./client";

/**
 * Portfolio items (/talents/me/portfolio-items) — the student's own certificate/work showcase.
 * docs/arastirma-ogrenci-profili.md §4. The badge is derived by the server; the client never sets it.
 */

export type PortfolioKind = "CERTIFICATE" | "WORK";
export type PortfolioBadge = "COORDINATOR_CONFIRMED" | "SELF_DECLARED" | "COORDINATOR_REJECTED";
export type CertificateDecision = "PENDING" | "CONFIRMED" | "REJECTED";

export const ABOUT_MAX_LENGTH = 1000;

export interface PortfolioItem {
  id: string;
  kind: PortfolioKind;
  title: string;
  issuer: string | null;
  issued_on: string | null;
  credential_id: string | null;
  external_url: string | null;
  evidence_id: string | null;
  show_on_profile: boolean;
  badge: PortfolioBadge;
  provider: string | null;
  created_at: string;
}

export interface EngagementCertificate {
  evidence_id: string;
  created_at: string;
  provider: string | null;
  credential_id: string | null;
  /** null: no certificate check requested yet. */
  decision: CertificateDecision | null;
  portfolio_item_id: string | null;
}

export interface PortfolioList {
  items: PortfolioItem[];
  engagement_certificates: EngagementCertificate[];
}

export interface PortfolioItemInput {
  kind: PortfolioKind;
  title: string;
  issuer?: string | null;
  issued_on?: string | null;
  credential_id?: string | null;
  external_url?: string | null;
  evidence_id?: string | null;
  show_on_profile?: boolean;
}

export type PortfolioItemPatch = Partial<Omit<PortfolioItemInput, "evidence_id">>;

const BASE = "/talents/me/portfolio-items";

export async function listPortfolio(): Promise<PortfolioList> {
  return (await apiFetch<PortfolioList>(BASE)) ?? { items: [], engagement_certificates: [] };
}

export async function createPortfolioItem(input: PortfolioItemInput): Promise<PortfolioItem | undefined> {
  return apiFetch<PortfolioItem>(BASE, { method: "POST", body: input });
}

export async function updatePortfolioItem(id: string, patch: PortfolioItemPatch): Promise<PortfolioItem | undefined> {
  return apiFetch<PortfolioItem>(`${BASE}/${encodeURIComponent(id)}`, { method: "PATCH", body: patch });
}

export async function deletePortfolioItem(id: string): Promise<void> {
  await apiFetch(`${BASE}/${encodeURIComponent(id)}`, { method: "DELETE" });
}
