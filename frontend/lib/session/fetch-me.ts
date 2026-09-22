// Hand-written: /me has no OpenAPI schema yet (PLAN 1.7). Replace with generated types when it does — see .claude/rules/frontend.md.

import { MeResponse, isMeResponse } from "./types";
import { apiFetch } from "@/lib/api/client";
import { InvalidResponseError } from "@/lib/api/errors";

/**
 * AC-1: Development fixture for /me response.
 * Used when NODE_ENV !== "production" to avoid network requests.
 */
export const devFixtureMe: MeResponse = {
  user: {
    id: "dev-user-1",
    email: "dev@yetkin360.test",
    full_name: "Geliştirici Kullanıcı",
  },
  organizations: [
    {
      id: "org-dev-1",
      name: "Test Kurumu",
    },
  ],
  institutions: [],
};

/**
 * AC-1/AC-7: Fetch /me from API.
 * - NODE_ENV !== "production": returns devFixtureMe without network call
 * - NODE_ENV === "production": calls apiFetch("/me"), validates response
 * - Validation failure: throws InvalidResponseError
 * - Errors from apiFetch: passed through unmodified (SessionExpiredError, NetworkError, ApiError)
 */
export async function fetchMe(): Promise<MeResponse> {
  // AC-1: Use fixture in development
  if (process.env.NODE_ENV !== "production") {
    return devFixtureMe;
  }

  // AC-7/AC-1: Production path — call apiFetch
  const response = await apiFetch<MeResponse>("/me");

  // AC-7: Validate response shape
  if (!isMeResponse(response)) {
    throw new InvalidResponseError("Sunucudan geçersiz yanıt alındı");
  }

  return response;
}
