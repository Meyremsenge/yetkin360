/**
 * YET-202/ENT-01: Engagement'a teslim (deliverable) ekleme.
 * POST /engagements/{id}/deliverables — sadece TALENT, sadece status=ACTIVE.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export interface CreateDeliverableInput {
  title: string;
  description?: string;
  skill_id?: string;
}

export interface DeliverableResponse {
  id: string;
  engagement_id: string;
  skill_id: string | null;
  title: string;
  description: string | null;
  submitted_by_user_id: string;
  submitted_at: string;
  created_at: string;
  updated_at: string;
}

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

export async function createDeliverable(
  engagementId: string,
  input: CreateDeliverableInput
): Promise<DeliverableResponse> {
  const response = await apiFetch<DeliverableResponse>(`/engagements/${engagementId}/deliverables`, {
    method: "POST",
    body: input,
  });
  if (!response) throw unexpectedResponse();
  return response;
}
