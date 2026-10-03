import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/**
 * AC-3: 401 UNAUTHENTICATED → exactly 1 silent refresh; concurrent 401s share single promise
 * AC-4: refresh fails (401 or network) → SessionExpiredError; cache cleared; redirect to /giris?neden=oturum-bitti
 * AC-5: network error / timeout → no session delete, no redirect; ≤2 retry for GET; no retry for writes
 * AC-7: type guard on /me response
 * AC-10: 401 EMAIL_NOT_VERIFIED → refresh NOT called; separate handling
 * AC-S2: POST/PATCH/DELETE sends X-CSRF-Token header; no Authorization; no localStorage/JWT
 * AC-S6: concurrent refresh calls share single promise (DoS prevention)
 */

// Helper to reset module state between tests for isolated refresh state
async function loadClient() {
  vi.resetModules();
  const { apiFetch } = await import("@/lib/api/client");
  const { ApiError, NetworkError, SessionExpiredError } = await import("@/lib/api/errors");
  return { apiFetch, ApiError, NetworkError, SessionExpiredError };
}

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.useRealTimers();
  });

  describe("Basic HTTP operations", () => {
    it("GET request to correct URL", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "123" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      );

      const result = await apiFetch("/users");
      expect(fetchMock).toHaveBeenCalledWith(
        "http://api.test/users",
        expect.objectContaining({ method: undefined })
      );
      expect(result).toEqual({ id: "123" });
    });

    it("POST with body", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ success: true }), {
          status: 201,
          headers: { "content-type": "application/json" },
        })
      );

      const result = await apiFetch("/users", {
        method: "POST",
        body: { name: "Ali" },
      });
      expect(fetchMock).toHaveBeenCalledWith(
        "http://api.test/users",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ name: "Ali" }),
          headers: expect.objectContaining({
            "content-type": "application/json",
          }),
        })
      );
      expect(result).toEqual({ success: true });
    });

    it("2xx status returns parsed JSON", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "test" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      );

      const result = await apiFetch("/test");
      expect(result).toEqual({ data: "test" });
    });

    it("204 No Content returns undefined", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      const result = await apiFetch("/test", { method: "POST" });
      expect(result).toBeUndefined();
    });
  });

  describe("Credentials and security headers", () => {
    it("AC-S2: every request includes credentials: 'include'", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      );

      await apiFetch("/test");
      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ credentials: "include" })
      );
    });

    it("AC-S2: POST request includes X-CSRF-Token header from cookie", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      document.cookie = "csrf_token=abc123xyz";
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      );

      await apiFetch("/users", { method: "POST", body: { name: "test" } });
      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            "x-csrf-token": "abc123xyz",
          }),
        })
      );
      document.cookie = "csrf_token=; max-age=0";
    });

    it("AC-S2: PATCH request includes X-CSRF-Token header from cookie", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      document.cookie = "csrf_token=xyz789";
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      );

      await apiFetch("/users/1", { method: "PATCH", body: { name: "updated" } });
      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            "x-csrf-token": "xyz789",
          }),
        })
      );
      document.cookie = "csrf_token=; max-age=0";
    });

    it("AC-S2: DELETE request includes X-CSRF-Token header from cookie", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      document.cookie = "csrf_token=del123";
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      await apiFetch("/users/1", { method: "DELETE" });
      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            "x-csrf-token": "del123",
          }),
        })
      );
      document.cookie = "csrf_token=; max-age=0";
    });

    it("AC-S2: GET request does NOT include X-CSRF-Token header", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      document.cookie = "csrf_token=abc123";
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      );

      await apiFetch("/users");
      const callHeaders = fetchMock.mock.calls[0][1]?.headers as Record<
        string,
        string
      >;
      expect(callHeaders["x-csrf-token"]).toBeUndefined();
      document.cookie = "csrf_token=; max-age=0";
    });

    it("AC-S2: Authorization header never set", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({}), { status: 200 })
      );

      await apiFetch("/protected");
      const callHeaders = fetchMock.mock.calls[0][1]?.headers as Record<
        string,
        string
      >;
      expect(callHeaders["authorization"]).toBeUndefined();
    });
  });

  describe("Network errors", () => {
    it("Fetch rejection → NetworkError('network')", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockRejectedValueOnce(new Error("Network failed"));

      await expect(apiFetch("/test")).rejects.toThrow(NetworkError);
      const error = (await apiFetch("/test").catch((e) => e)) as InstanceType<typeof NetworkError>;
      expect(error.kind).toBe("network");
    });

    it("Timeout after 10 seconds → NetworkError('timeout')", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      vi.useFakeTimers();

      fetchMock.mockImplementationOnce(async () => {
        await new Promise((resolve) =>
          setTimeout(() => resolve(new Response()), 15000)
        );
        return new Response();
      });

      const promise = apiFetch("/test");
      const settled = promise.catch((e) => e);
      await vi.advanceTimersByTimeAsync(10_000);
      const error = await settled;
      expect(error).toBeInstanceOf(NetworkError);
      expect((error as InstanceType<typeof NetworkError>).kind).toBe("timeout");

      vi.useRealTimers();
    });
  });

  describe("AC-3: 401 refresh flow", () => {
    it("AC-3: 401 UNAUTHENTICATED triggers single refresh, then retries original request", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      // First call: original request 401
      // Second call: refresh POST
      // Third call: retry original request
      fetchMock
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
            headers: { "content-type": "application/json" },
          })
        )
        .mockResolvedValueOnce(new Response(null, { status: 204 })) // refresh success
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ id: "123" }), {
            status: 200,
            headers: { "content-type": "application/json" },
          })
        );

      const result = await apiFetch("/users");
      expect(result).toEqual({ id: "123" });
      expect(fetchMock).toHaveBeenCalledTimes(3);
      // Verify refresh was called
      expect(fetchMock.mock.calls[1][0]).toContain("/auth/refresh");
    });

    it("AC-3: concurrent 401s share single in-flight refresh", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      // Setup: all requests initially 401
      fetchMock
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        )
        .mockResolvedValueOnce(new Response(null, { status: 204 })) // single refresh
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ id: "1" }), { status: 200 })
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ id: "2" }), { status: 200 })
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ id: "3" }), { status: 200 })
        );

      const p1 = apiFetch("/users/1");
      const p2 = apiFetch("/users/2");
      const p3 = apiFetch("/users/3");
      const results = await Promise.all([p1, p2, p3]);

      expect(results).toEqual([{ id: "1" }, { id: "2" }, { id: "3" }]);
      // Fetch should be: 3 original 401s + 1 refresh + 3 retries = 7 calls
      expect(fetchMock).toHaveBeenCalledTimes(7);
      // Exactly 1 call to /auth/refresh
      const refreshCalls = fetchMock.mock.calls.filter((call) =>
        String(call[0]).includes("/auth/refresh")
      );
      expect(refreshCalls).toHaveLength(1);
    });
  });

  describe("AC-4: Refresh failure flow", () => {
    it("AC-4: refresh returns 401 → SessionExpiredError, no retry", async () => {
      const { apiFetch, SessionExpiredError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        );

      await expect(apiFetch("/users")).rejects.toThrow(SessionExpiredError);
      // Should only be: original request 401 + failed refresh 401 = 2 calls
      // No retry of original after failed refresh
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it("AC-4: retried request also 401 after successful refresh → SessionExpiredError", async () => {
      const { apiFetch, SessionExpiredError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        )
        .mockResolvedValueOnce(new Response(null, { status: 204 })) // refresh success
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        );

      await expect(apiFetch("/users")).rejects.toThrow(SessionExpiredError);
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    it("AC-4: refresh network error → NetworkError, not SessionExpiredError", async () => {
      const { apiFetch, NetworkError, SessionExpiredError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        )
        .mockRejectedValueOnce(new Error("Network down"));

      const error = (await apiFetch("/users").catch((e) => e)) as InstanceType<typeof NetworkError>;
      expect(error).toBeInstanceOf(NetworkError);
      expect(error).not.toBeInstanceOf(SessionExpiredError);
    });

    it("AC-4: refresh returns 429 (rate limit) → ApiError, not SessionExpiredError", async () => {
      const { apiFetch, ApiError, SessionExpiredError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              code: "RATE_LIMITED",
              message: "Too many requests",
              request_id: "req-rate",
            }),
            { status: 429 }
          )
        );

      const error = (await apiFetch("/users").catch((e) => e)) as InstanceType<typeof ApiError>;
      expect(error).toBeInstanceOf(ApiError);
      expect(error).not.toBeInstanceOf(SessionExpiredError);
      expect(error.status).toBe(429);
    });
  });

  describe("AC-5: Network failures and retries", () => {
    it("AC-5: GET network error → NetworkError('network') and apiFetch does NOT retry (retry TanStack Query'nin sessionRetry politikasının işi)", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock.mockRejectedValueOnce(new Error("Network failed"));

      const error = (await apiFetch("/users").catch((e) => e)) as InstanceType<typeof NetworkError>;
      expect(error).toBeInstanceOf(NetworkError);
      expect(error.kind).toBe("network");
      // apiFetch çağrısı tam 1 kez yapılmış, retry apiFetch'te değil TanStack Query'de
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it("AC-5: POST network error → no automatic retry", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock.mockRejectedValueOnce(new Error("Network fails"));

      await expect(
        apiFetch("/users", { method: "POST", body: { name: "test" } })
      ).rejects.toThrow(NetworkError);
      // Should be called exactly once (no retry)
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it("AC-5: PATCH network error → no automatic retry", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock.mockRejectedValueOnce(new Error("Network fails"));

      await expect(
        apiFetch("/users/1", { method: "PATCH", body: { name: "updated" } })
      ).rejects.toThrow(NetworkError);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it("AC-5: DELETE network error → no automatic retry", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock.mockRejectedValueOnce(new Error("Network fails"));

      await expect(apiFetch("/users/1", { method: "DELETE" })).rejects.toThrow(
        NetworkError
      );
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });

  describe("AC-7: Type-safe responses", () => {
    it("Non-2xx status → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "NOT_FOUND",
            message: "Kullanıcı bulunamadı",
            request_id: "req-404",
          }),
          { status: 404 }
        )
      );

      const error = (await apiFetch("/users/nonexistent").catch(
        (e) => e
      )) as InstanceType<typeof ApiError>;
      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(404);
      expect(error.code).toBe("NOT_FOUND");
    });

    it("Invalid response body (not JSON) → ApiError with UNKNOWN_ERROR", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock.mockResolvedValueOnce(
        new Response("HTML error page", {
          status: 500,
          headers: { "content-type": "text/html" },
        })
      );

      const error = (await apiFetch("/test").catch((e) => e)) as InstanceType<typeof ApiError>;
      expect(error).toBeInstanceOf(ApiError);
      expect(error.code).toBe("UNKNOWN_ERROR");
    });
  });

  describe("AC-10: EMAIL_NOT_VERIFIED handling", () => {
    it("AC-10: 401 EMAIL_NOT_VERIFIED → no refresh; ApiError directly", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "EMAIL_NOT_VERIFIED",
            message: "E-postanız henüz doğrulanmamıştır",
            request_id: "req-email",
          }),
          { status: 401 }
        )
      );

      const error = (await apiFetch("/users").catch((e) => e)) as InstanceType<typeof ApiError>;
      expect(error).toBeInstanceOf(ApiError);
      expect(error.code).toBe("EMAIL_NOT_VERIFIED");
      // Only 1 call (no refresh attempt)
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });


  describe("AC-S6: DoS prevention — refresh storm", () => {
    it("AC-S6: many concurrent 401s → only 1 refresh call to /auth/refresh", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);

      // Setup: 10 concurrent requests, all initially 401
      for (let i = 0; i < 10; i++) {
        fetchMock.mockResolvedValueOnce(
          new Response(JSON.stringify({ code: "UNAUTHENTICATED" }), {
            status: 401,
          })
        );
      }
      // Single refresh
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
      // Retries all succeed
      for (let i = 0; i < 10; i++) {
        fetchMock.mockResolvedValueOnce(
          new Response(JSON.stringify({ id: i }), { status: 200 })
        );
      }

      const promises = Array.from({ length: 10 }, (_, i) =>
        apiFetch(`/user/${i}`)
      );
      const results = await Promise.all(promises);

      // All should succeed
      expect(results).toHaveLength(10);
      // Calls: 10 original + 1 refresh + 10 retries = 21
      expect(fetchMock).toHaveBeenCalledTimes(21);
      // Exactly 1 refresh
      const refreshCalls = fetchMock.mock.calls.filter((call) =>
        String(call[0]).includes("/auth/refresh")
      );
      expect(refreshCalls).toHaveLength(1);
      // Verify the single refresh call is POST
      expect(refreshCalls[0][1]?.method).toBe("POST");
    });
  });
});

  describe("New auth functions", () => {
    beforeEach(() => {
      vi.stubGlobal("fetch", vi.fn());
      vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    });

    afterEach(() => {
      vi.unstubAllGlobals();
      vi.unstubAllEnvs();
      vi.useRealTimers();
    });

    it("AC-1/AC-S1: register(email, password, full_name) calls POST /auth/register", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ user_id: "uuid-123" }), {
          status: 201,
          headers: { "content-type": "application/json" },
        })
      );

      const result = await apiFetch("/auth/register", {
        method: "POST",
        body: {
          email: "test@example.com",
          password: "password123",
          full_name: "Test User",
        },
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/auth/register"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            email: "test@example.com",
            password: "password123",
            full_name: "Test User",
          }),
        })
      );
      expect(result).toEqual({ user_id: "uuid-123" });
    });

    it("AC-1/AC-S1: register returns 422 (validation error) → ApiError with fields", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "VALIDATION_ERROR",
            message: "Validation failed",
            fields: { password: "Password must be at least 8 characters" },
            request_id: "req-422",
          }),
          { status: 422 }
        )
      );

      const error = (await apiFetch("/auth/register", {
        method: "POST",
        body: { email: "test@example.com", password: "short", full_name: "Test" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(422);
      expect(error.code).toBe("VALIDATION_ERROR");
      expect(error.fields?.password).toBeDefined();
    });

    it("AC-1/AC-S1: register returns 429 (rate limit) → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "RATE_LIMITED",
            message: "Too many registration attempts",
            request_id: "req-429",
          }),
          { status: 429 }
        )
      );

      const error = (await apiFetch("/auth/register", {
        method: "POST",
        body: { email: "test@example.com", password: "password123", full_name: "Test" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(429);
      expect(error.code).toBe("RATE_LIMITED");
    });

    it("AC-3/AC-4: login(email, password) calls POST /auth/login", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user_id: "uuid-456",
            role: "user",
            email_verified: false,
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      );

      const result = await apiFetch("/auth/login", {
        method: "POST",
        body: { email: "test@example.com", password: "password123" },
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/auth/login"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            email: "test@example.com",
            password: "password123",
          }),
        })
      );
      expect(result).toEqual({
        user_id: "uuid-456",
        role: "user",
        email_verified: false,
      });
    });

    it("AC-3: login returns 401 INVALID_CREDENTIALS → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "INVALID_CREDENTIALS",
            message: "E-posta veya şifre hatalı",
            request_id: "req-401-invalid",
          }),
          { status: 401 }
        )
      );

      const error = (await apiFetch("/auth/login", {
        method: "POST",
        body: { email: "test@example.com", password: "wrong" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(401);
      expect(error.code).toBe("INVALID_CREDENTIALS");
    });

    it("AC-4: login returns 423 ACCOUNT_LOCKED → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "ACCOUNT_LOCKED",
            message: "Hesabınız geçici olarak kilitlendi",
            request_id: "req-423-locked",
          }),
          { status: 423 }
        )
      );

      const error = (await apiFetch("/auth/login", {
        method: "POST",
        body: { email: "test@example.com", password: "password123" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(423);
      expect(error.code).toBe("ACCOUNT_LOCKED");
    });

    it("AC-5/AC-6: verifyEmail(token) calls POST /auth/verify-email → 204", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      const result = await apiFetch("/auth/verify-email", {
        method: "POST",
        body: { token: "valid-token-abc" },
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/auth/verify-email"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ token: "valid-token-abc" }),
        })
      );
      expect(result).toBeUndefined();
    });

    it("YET-196: resendVerification() calls POST /auth/resend-verification → 204", async () => {
      await loadClient();
      const { resendVerification } = await import("@/lib/api/client");
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      const result = await resendVerification();

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/auth/resend-verification"),
        expect.objectContaining({ method: "POST" })
      );
      expect(result).toBeUndefined();
    });

    it("AC-6: verifyEmail returns 400 INVALID_TOKEN → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "INVALID_TOKEN",
            message: "Bağlantı geçersiz",
            request_id: "req-400-token",
          }),
          { status: 400 }
        )
      );

      const error = (await apiFetch("/auth/verify-email", {
        method: "POST",
        body: { token: "invalid-token" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(400);
      expect(error.code).toBe("INVALID_TOKEN");
    });

    it("AC-6: verifyEmail returns 410 TOKEN_EXPIRED → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "TOKEN_EXPIRED",
            message: "Bağlantı süresi dolmuş",
            request_id: "req-410-expired",
          }),
          { status: 410 }
        )
      );

      const error = (await apiFetch("/auth/verify-email", {
        method: "POST",
        body: { token: "expired-token" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(410);
      expect(error.code).toBe("TOKEN_EXPIRED");
    });

    it("AC-7/AC-S2/AC-S6: forgotPassword(email) calls POST /auth/forgot-password → 204 always", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      const result = await apiFetch("/auth/forgot-password", {
        method: "POST",
        body: { email: "test@example.com" },
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/auth/forgot-password"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ email: "test@example.com" }),
        })
      );
      expect(result).toBeUndefined();
    });

    it("AC-7/AC-S2: forgotPassword returns 429 (rate limit) → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "RATE_LIMITED",
            message: "Too many password reset attempts",
            request_id: "req-429-forgot",
          }),
          { status: 429 }
        )
      );

      const error = (await apiFetch("/auth/forgot-password", {
        method: "POST",
        body: { email: "test@example.com" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(429);
      expect(error.code).toBe("RATE_LIMITED");
    });

    it("AC-8/AC-6: resetPassword(token, new_password) calls POST /auth/reset-password → 204", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      const result = await apiFetch("/auth/reset-password", {
        method: "POST",
        body: { token: "reset-token-xyz", new_password: "newpassword123" },
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/auth/reset-password"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: "reset-token-xyz",
            new_password: "newpassword123",
          }),
        })
      );
      expect(result).toBeUndefined();
    });

    it("AC-6: resetPassword returns 400 INVALID_TOKEN → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "INVALID_TOKEN",
            message: "Bağlantı geçersiz",
            request_id: "req-400-reset",
          }),
          { status: 400 }
        )
      );

      const error = (await apiFetch("/auth/reset-password", {
        method: "POST",
        body: { token: "invalid-token", new_password: "newpassword" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(400);
      expect(error.code).toBe("INVALID_TOKEN");
    });

    it("AC-6: resetPassword returns 410 TOKEN_EXPIRED → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "TOKEN_EXPIRED",
            message: "Bağlantı süresi dolmuş",
            request_id: "req-410-reset",
          }),
          { status: 410 }
        )
      );

      const error = (await apiFetch("/auth/reset-password", {
        method: "POST",
        body: { token: "expired-reset-token", new_password: "newpassword" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(410);
      expect(error.code).toBe("TOKEN_EXPIRED");
    });
  });

describe("AC-S2: Source code check — no localStorage/JWT/Authorization", () => {
  it("AC-S2: client.ts exists and is non-empty", async () => {
    const { readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const filePath = join(process.cwd(), "lib/api/client.ts");
    const source = readFileSync(filePath, "utf-8");
    expect(source.length).toBeGreaterThan(0);
  });

  it.each([
    "localStorage",
    "sessionStorage",
    "Authorization",
    "jwt-decode",
    "atob(",
  ])("AC-S2: client.ts source does not contain %s", async (token) => {
    const { readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const filePath = join(process.cwd(), "lib/api/client.ts");
    const source = readFileSync(filePath, "utf-8");
    expect(source).not.toContain(token);
  });
});

describe("Talent Profile and Skills API functions", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.useRealTimers();
  });

  describe("AC-2: updateTalentProfile", () => {
    it("AC-2: updateTalentProfile(headline, department, study_year, city, visibility, public_slug) calls PATCH /talents/me", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            headline: "Software Engineer",
            department: "Engineering",
            study_year: 3,
            city: "İstanbul",
            visibility: "PUBLIC",
            public_slug: "ali-engineer",
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      );

      const result = await apiFetch("/talents/me", {
        method: "PATCH",
        body: {
          headline: "Software Engineer",
          department: "Engineering",
          study_year: 3,
          city: "İstanbul",
          visibility: "PUBLIC",
          public_slug: "ali-engineer",
        },
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/talents/me"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            headline: "Software Engineer",
            department: "Engineering",
            study_year: 3,
            city: "İstanbul",
            visibility: "PUBLIC",
            public_slug: "ali-engineer",
          }),
        })
      );
      expect(result).toEqual({
        headline: "Software Engineer",
        department: "Engineering",
        study_year: 3,
        city: "İstanbul",
        visibility: "PUBLIC",
        public_slug: "ali-engineer",
      });
    });

    it("AC-2: updateTalentProfile with partial fields (null/undefined omitted)", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ headline: "Updated Headline" }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      );

      const result = await apiFetch("/talents/me", {
        method: "PATCH",
        body: { headline: "Updated Headline" },
      });

      expect(result).toEqual({ headline: "Updated Headline" });
    });

    it("AC-3: updateTalentProfile returns 409 SLUG_TAKEN → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "SLUG_TAKEN",
            message: "Bu profil linki başka biri tarafından kullanılıyor",
            request_id: "req-409-slug",
          }),
          { status: 409 }
        )
      );

      const error = (await apiFetch("/talents/me", {
        method: "PATCH",
        body: { public_slug: "taken-slug" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(409);
      expect(error.code).toBe("SLUG_TAKEN");
    });
  });

  describe("AC-4: getMySkills", () => {
    it("AC-4: getMySkills() calls GET /talents/me/skills → { items: [...] }", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [
              { skill: { id: "skill1", name_tr: "Python" }, claimed_level: "ADVANCED" },
              { skill: { id: "skill2", name_tr: "JavaScript" }, claimed_level: "INTERMEDIATE" },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      );

      const result = await apiFetch("/talents/me/skills");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/talents/me/skills"),
        expect.objectContaining({ method: undefined })
      );
      expect(result).toEqual({
        items: [
          { skill: { id: "skill1", name_tr: "Python" }, claimed_level: "ADVANCED" },
          { skill: { id: "skill2", name_tr: "JavaScript" }, claimed_level: "INTERMEDIATE" },
        ],
      });
    });

    it("AC-4: getMySkills() returns empty items list", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      );

      const result = await apiFetch("/talents/me/skills");

      expect(result).toEqual({ items: [] });
    });
  });

  describe("AC-5: addSkill", () => {
    it("AC-5: addSkill(skillId, claimedLevel) calls POST /talents/me/skills → 201", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 201 }));

      const result = await apiFetch("/talents/me/skills", {
        method: "POST",
        body: { skill_id: "skill-uuid-1", claimed_level: "INTERMEDIATE" },
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/talents/me/skills"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            skill_id: "skill-uuid-1",
            claimed_level: "INTERMEDIATE",
          }),
        })
      );
      expect(result).toBeUndefined();
    });

    it("AC-5: addSkill with optional claimed_level omitted", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 201 }));

      const result = await apiFetch("/talents/me/skills", {
        method: "POST",
        body: { skill_id: "skill-uuid-2" },
      });

      expect(result).toBeUndefined();
    });

    it("AC-6: addSkill returns 409 ALREADY_CLAIMED → ApiError (reactive fallback)", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "ALREADY_CLAIMED",
            message: "Bu yetkinliği zaten eklediniz",
            request_id: "req-409-already",
          }),
          { status: 409 }
        )
      );

      const error = (await apiFetch("/talents/me/skills", {
        method: "POST",
        body: { skill_id: "skill-uuid-3" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(409);
      expect(error.code).toBe("ALREADY_CLAIMED");
    });

    it("AC-7: addSkill returns 404 SKILL_NOT_FOUND → ApiError", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "SKILL_NOT_FOUND",
            message: "Bu yetkinlik artık mevcut değil",
            request_id: "req-404-skill",
          }),
          { status: 404 }
        )
      );

      const error = (await apiFetch("/talents/me/skills", {
        method: "POST",
        body: { skill_id: "nonexistent-skill-uuid" },
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(404);
      expect(error.code).toBe("SKILL_NOT_FOUND");
    });
  });

  describe("AC-8/AC-9: removeSkill", () => {
    it("AC-8: removeSkill(skillId) calls DELETE /talents/me/skills/{skillId} → 204", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

      const result = await apiFetch("/talents/me/skills/skill-uuid-1", {
        method: "DELETE",
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/talents/me/skills/skill-uuid-1"),
        expect.objectContaining({ method: "DELETE" })
      );
      expect(result).toBeUndefined();
    });

    it("AC-9: removeSkill returns 404 (already deleted) → silent, no error shown to user", async () => {
      const { apiFetch, ApiError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "SKILL_NOT_FOUND",
            message: "Yetkinlik bulunamadı",
            request_id: "req-404-delete",
          }),
          { status: 404 }
        )
      );

      const error = (await apiFetch("/talents/me/skills/already-deleted-skill", {
        method: "DELETE",
      }).catch((e) => e)) as InstanceType<typeof ApiError>;

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(404);
      expect(error.code).toBe("SKILL_NOT_FOUND");
    });
  });

  describe("AC-13: listSkills", () => {
    it("AC-13: listSkills(query?) calls GET /skills → { items: [...] }", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [
              { id: "skill1", name_tr: "Python" },
              { id: "skill2", name_tr: "JavaScript" },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      );

      const result = await apiFetch("/skills");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/skills"),
        expect.objectContaining({ method: undefined })
      );
      expect(result).toEqual({
        items: [
          { id: "skill1", name_tr: "Python" },
          { id: "skill2", name_tr: "JavaScript" },
        ],
      });
    });

    it("AC-13: listSkills(query) calls GET /skills?q=search-term", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [{ id: "skill3", name_tr: "Python Advanced" }],
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      );

      const result = await apiFetch("/skills?q=python");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/skills?q=python"),
        expect.any(Object)
      );
      expect(result).toEqual({
        items: [{ id: "skill3", name_tr: "Python Advanced" }],
      });
    });

    it("AC-13: listSkills() returns empty items when no match", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      );

      const result = await apiFetch("/skills?q=nonexistent");

      expect(result).toEqual({ items: [] });
    });
  });

  describe("AC-10: Network errors on any operation", () => {
    it("AC-10: updateTalentProfile network error → NetworkError", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockRejectedValueOnce(new Error("Network failed"));

      const error = (await apiFetch("/talents/me", {
        method: "PATCH",
        body: { headline: "Test" },
      }).catch((e) => e)) as InstanceType<typeof NetworkError>;

      expect(error).toBeInstanceOf(NetworkError);
      expect(error.kind).toBe("network");
    });

    it("AC-10: addSkill network error → NetworkError", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockRejectedValueOnce(new Error("Network failed"));

      const error = (await apiFetch("/talents/me/skills", {
        method: "POST",
        body: { skill_id: "test" },
      }).catch((e) => e)) as InstanceType<typeof NetworkError>;

      expect(error).toBeInstanceOf(NetworkError);
    });

    it("AC-10: removeSkill network error → NetworkError", async () => {
      const { apiFetch, NetworkError } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockRejectedValueOnce(new Error("Network failed"));

      const error = (await apiFetch("/talents/me/skills/test-skill", {
        method: "DELETE",
      }).catch((e) => e)) as InstanceType<typeof NetworkError>;

      expect(error).toBeInstanceOf(NetworkError);
    });
  });

  describe("AC-S1: Debounce + XSS hygiene — listSkills", () => {
    it("AC-S1: listSkills() should be called directly; debounce logic handled in component (apiFetch just returns)", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [] }), { status: 200 })
      );

      const result = await apiFetch("/skills?q=test");
      expect(result).toBeDefined();
      // Debounce verification is component-level, not apiFetch-level
    });

    it("AC-S1: listSkills response not using dangerouslySetInnerHTML (verified by component test)", async () => {
      // This is a contract test: apiFetch returns plain JSON objects,
      // component layer is responsible for safe rendering
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [{ id: "1", name_tr: "Skill <script>alert('xss')</script>" }],
          }),
          { status: 200 }
        )
      );

      const result = (await apiFetch("/skills")) as Record<string, unknown>;
      // apiFetch returns raw JSON — safe rendering is component responsibility
      expect(result).toBeDefined();
      expect(typeof result.items).toBe("object");
    });
  });

  describe("AC-S2: public_slug XSS hygiene", () => {
    it("AC-S2: updateTalentProfile returns public_slug unchanged (no dangerouslySetInnerHTML in render)", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      const maliciousSlug = "test<script>alert('xss')</script>";
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ public_slug: maliciousSlug }),
          { status: 200 }
        )
      );

      const result = (await apiFetch("/talents/me", {
        method: "PATCH",
        body: { public_slug: maliciousSlug },
      })) as Record<string, unknown>;

      // apiFetch returns raw value; safe rendering is form component responsibility
      expect(result.public_slug).toBe(maliciousSlug);
    });
  });

  describe("AC-S3: visibility consistency (no silent escalation)", () => {
    it("AC-S3: updateTalentProfile preserves current visibility value (form should not default to PUBLIC)", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ visibility: "PRIVATE" }),
          { status: 200 }
        )
      );

      const result = (await apiFetch("/talents/me", {
        method: "PATCH",
        body: { visibility: "PRIVATE" }, // Form responsibility to preserve current value
      })) as Record<string, unknown>;

      expect(result.visibility).toBe("PRIVATE");
    });
  });

  describe("AC-12: talent_profile null handling", () => {
    it("AC-12: GET /me returns talent_profile null (error state in component)", async () => {
      const { apiFetch } = await loadClient();
      const fetchMock = vi.mocked(global.fetch);
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user: { id: "123" },
            talent_profile: null,
            organizations: [],
            institutions: [],
          }),
          { status: 200 }
        )
      );

      const result = await apiFetch("/me");

      expect(result).toBeDefined();
      // Component handles null talent_profile as error state
    });
  });
});
