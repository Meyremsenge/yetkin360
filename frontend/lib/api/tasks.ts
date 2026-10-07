/**
 * YET-202/ENT-01: Engagement için görev (task) oluşturma.
 * POST /engagements/{id}/tasks — ORG_MEMBER/ORG_ADMIN/INST_COORD (TALENT 403),
 * sadece status=ACTIVE.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export interface CreateTaskInput {
  title: string;
  description?: string;
  due_at?: string;
  skill_id?: string;
}

export interface TaskResponse {
  id: string;
  title: string;
  status: string;
}

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

export async function createTask(engagementId: string, input: CreateTaskInput): Promise<TaskResponse> {
  const response = await apiFetch<TaskResponse>(`/engagements/${engagementId}/tasks`, {
    method: "POST",
    body: input,
  });
  if (!response) throw unexpectedResponse();
  return response;
}
