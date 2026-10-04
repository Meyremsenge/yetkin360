/**
 * YET-202/ENT-01: Engagement için tanıklık (attestation) verme.
 * POST /engagements/{id}/attestations — sadece COORDINATOR (institution_id varsa) /
 * ORG_ADMIN (institution_id yoksa), sadece status=EVALUATED (T8 geçişi).
 *
 * downgrade_reasons dolu olsa bile yanıt 201'dir (COMPETENCE → PARTICIPATION'a
 * düşmüş olabilir, bu bir hata değil — bkz. docs/DOMAIN.md §3.11).
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export type ClaimType = "PARTICIPATION" | "CONTRIBUTION" | "COMPETENCE" | "CONDUCT";

export interface CreateAttestationInput {
  claim_type: ClaimType;
  version: number;
  skill_id?: string;
}

export interface AttestationResponse {
  id: string;
  claim_type: string;
  requested_claim_type: string;
  downgrade_reasons: string[];
}

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

export async function createAttestation(
  engagementId: string,
  input: CreateAttestationInput
): Promise<AttestationResponse> {
  const response = await apiFetch<AttestationResponse>(`/engagements/${engagementId}/attestations`, {
    method: "POST",
    body: input,
  });
  if (!response) throw unexpectedResponse();
  return response;
}
