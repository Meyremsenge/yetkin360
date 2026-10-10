/**
 * YET-202/ENT-01: Engagement için görev (task) oluşturma ve doğrulama.
 * POST /engagements/{id}/tasks
 *   - kuruluş üyesi / koordinatör: yalnız status=ACTIVE, görev doğrulanmış oluşur
 *   - öğrenci (kendi çalışması): DRAFT veya ACTIVE, görev doğrulanmamış oluşur
 * POST /engagements/{id}/tasks/{taskId}/verify — yalnız kuruluş üyesi / koordinatör.
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
  verified: boolean;
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

/** 403: öğrenci kendi görevini onaylayamaz; 409 TASK_ALREADY_VERIFIED: görev zaten doğrulanmış. */
export async function verifyTask(engagementId: string, taskId: string): Promise<TaskResponse> {
  const response = await apiFetch<TaskResponse>(`/engagements/${engagementId}/tasks/${taskId}/verify`, {
    method: "POST",
  });
  if (!response) throw unexpectedResponse();
  return response;
}
