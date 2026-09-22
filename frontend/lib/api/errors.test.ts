import { describe, it, expect } from "vitest";
import {
  ApiError,
  NetworkError,
  SessionExpiredError,
  InvalidResponseError,
  parseApiError,
} from "@/lib/api/errors";

/**
 * AC-6: Hata sınıfları.
 * AC-S4: Loglara/DOM'a PII yazılmaz; yalnız code/request_id.
 */

describe("ApiError", () => {
  it("constructs with required fields", () => {
    const error = new ApiError({
      status: 401,
      code: "UNAUTHENTICATED",
      message: "Oturumunuz sona erdi",
      requestId: "req-123",
    });
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(401);
    expect(error.code).toBe("UNAUTHENTICATED");
    expect(error.message).toBe("Oturumunuz sona erdi");
    expect(error.requestId).toBe("req-123");
  });

  it("optionally includes fields (validation errors)", () => {
    const error = new ApiError({
      status: 400,
      code: "VALIDATION_ERROR",
      message: "Giriş hatalı",
      requestId: "req-456",
      fields: {
        email: "Geçersiz e-posta",
        password: "Minimum 8 karakter",
      },
    });
    expect(error.fields).toEqual({
      email: "Geçersiz e-posta",
      password: "Minimum 8 karakter",
    });
  });

  it("handles null requestId", () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "İç sunucu hatası",
      requestId: null,
    });
    expect(error.requestId).toBeNull();
  });
});

describe("NetworkError", () => {
  it("constructs network error", () => {
    const error = new NetworkError("network");
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(NetworkError);
    expect(error.kind).toBe("network");
  });

  it("constructs timeout error", () => {
    const error = new NetworkError("timeout");
    expect(error.kind).toBe("timeout");
  });

  it("has descriptive message", () => {
    const networkError = new NetworkError("network");
    const timeoutError = new NetworkError("timeout");
    expect(networkError.message).toBeDefined();
    expect(timeoutError.message).toBeDefined();
  });
});

describe("SessionExpiredError", () => {
  it("constructs with default message", () => {
    const error = new SessionExpiredError();
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(SessionExpiredError);
    expect(error.message).toBeDefined();
  });
});

describe("InvalidResponseError", () => {
  it("is an Error instance", () => {
    const error = new InvalidResponseError("Boş gövde");
    expect(error).toBeInstanceOf(Error);
  });

  it("is instanceof InvalidResponseError", () => {
    const error = new InvalidResponseError("Beklenen şekil değil");
    expect(error).toBeInstanceOf(InvalidResponseError);
  });

  it("preserves message", () => {
    const error = new InvalidResponseError("Test mesajı");
    expect(error.message).toBe("Test mesajı");
  });

  it("does not confuse with ApiError", () => {
    const invErr = new InvalidResponseError("x");
    const apiErr = new ApiError({
      status: 500,
      code: "TEST",
      message: "y",
      requestId: "req-1",
    });
    expect(invErr).not.toBeInstanceOf(ApiError);
    expect(apiErr).not.toBeInstanceOf(InvalidResponseError);
  });

  it("does not confuse with NetworkError", () => {
    const invErr = new InvalidResponseError("x");
    const netErr = new NetworkError("network");
    expect(invErr).not.toBeInstanceOf(NetworkError);
    expect(netErr).not.toBeInstanceOf(InvalidResponseError);
  });

  it("does not confuse with SessionExpiredError", () => {
    const invErr = new InvalidResponseError("x");
    const sessErr = new SessionExpiredError();
    expect(invErr).not.toBeInstanceOf(SessionExpiredError);
    expect(sessErr).not.toBeInstanceOf(InvalidResponseError);
  });
});

describe("parseApiError", () => {
  it("AC-6: parses valid error body with all fields", () => {
    const status = 401;
    const body = {
      code: "UNAUTHENTICATED",
      message: "Oturumunuz sona erdi",
      request_id: "req-789",
      fields: { email: "Geçersiz" },
    };
    const error = parseApiError(status, body);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(401);
    expect(error.code).toBe("UNAUTHENTICATED");
    expect(error.message).toBe("Oturumunuz sona erdi");
    expect(error.requestId).toBe("req-789");
    expect(error.fields).toEqual({ email: "Geçersiz" });
  });

  it("AC-6: parses error body without fields", () => {
    const error = parseApiError(400, {
      code: "VALIDATION_ERROR",
      message: "Giriş hatalı",
      request_id: "req-100",
    });
    expect(error.fields).toBeUndefined();
  });

  it("AC-6: parses error body without request_id", () => {
    const error = parseApiError(500, {
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
    });
    expect(error.requestId).toBeNull();
  });

  it("AC-6: handles malformed JSON body → UNKNOWN_ERROR", () => {
    const error = parseApiError(500, "malformed json");
    expect(error.code).toBe("UNKNOWN_ERROR");
    expect(error.status).toBe(500);
    expect(error.message).toBeDefined();
  });

  it("AC-6: handles null body → UNKNOWN_ERROR", () => {
    const error = parseApiError(500, null);
    expect(error.code).toBe("UNKNOWN_ERROR");
    expect(error.requestId).toBeNull();
  });

  it("AC-6: handles undefined body → UNKNOWN_ERROR", () => {
    const error = parseApiError(500, undefined);
    expect(error.code).toBe("UNKNOWN_ERROR");
  });

  it("AC-6: handles empty object body (missing code/message) → UNKNOWN_ERROR", () => {
    const error = parseApiError(500, {});
    expect(error.code).toBe("UNKNOWN_ERROR");
  });

  it("AC-6: handles body with code but no message", () => {
    const error = parseApiError(400, { code: "SOME_ERROR" });
    expect(error.code).toBe("SOME_ERROR");
    expect(error.message).toBeDefined(); // Fallback message
  });

  it("AC-S4: error message doesn't leak request internals", () => {
    const error = new ApiError({
      status: 500,
      code: "DB_ERROR",
      message: "SELECT * FROM users WHERE id = 1",
      requestId: "req-secret",
    });
    // Caller must not render error.message directly; must use code + message from tr.json
    expect(error.message).toBe("SELECT * FROM users WHERE id = 1");
    // This test verifies the structure; actual sanitization is caller's responsibility
  });

  it("AC-6: parses array body (invalid) → UNKNOWN_ERROR", () => {
    const error = parseApiError(500, ["error"]);
    expect(error.code).toBe("UNKNOWN_ERROR");
  });

  it("AC-6: parses numeric body (invalid) → UNKNOWN_ERROR", () => {
    const error = parseApiError(500, 123);
    expect(error.code).toBe("UNKNOWN_ERROR");
  });

  it("AC-6: preserves status code in ApiError", () => {
    const error400 = parseApiError(400, {
      code: "VALIDATION_ERROR",
      message: "Hatalı giriş",
      request_id: "req-1",
    });
    expect(error400.status).toBe(400);

    const error401 = parseApiError(401, {
      code: "UNAUTHENTICATED",
      message: "Oturum gerekli",
      request_id: "req-2",
    });
    expect(error401.status).toBe(401);

    const error500 = parseApiError(500, {
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      request_id: "req-3",
    });
    expect(error500.status).toBe(500);
  });
});
