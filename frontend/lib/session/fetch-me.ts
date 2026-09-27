// Hand-written: /me has no OpenAPI schema yet (PLAN 1.7). Replace with generated types when it does — see .claude/rules/frontend.md.

import { MeResponse, isMeResponse } from "./types";
import { apiFetch } from "@/lib/api/client";
import { InvalidResponseError } from "@/lib/api/errors";

/**
 * AC-7: Fetch /me from API.
 * - Calls apiFetch("/me"), validates response
 * - Validation failure: throws InvalidResponseError
 * - Errors from apiFetch: passed through unmodified (SessionExpiredError, NetworkError, ApiError)
 */
export async function fetchMe(): Promise<MeResponse> {
  const response = await apiFetch<MeResponse>("/me");

  // AC-7: Validate response shape
  if (!isMeResponse(response)) {
    throw new InvalidResponseError("Sunucudan geçersiz yanıt alındı");
  }

  return response;
}
