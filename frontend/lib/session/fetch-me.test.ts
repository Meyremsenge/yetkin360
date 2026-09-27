import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchMe } from "@/lib/session/fetch-me";
import {
  InvalidResponseError,
  SessionExpiredError,
  NetworkError,
  ApiError,
} from "@/lib/api/errors";
import { isMeResponse } from "@/lib/session/types";

vi.mock("@/lib/api/client");

/**
 * AC-1: /me fetch'i — geçerli oturum, boş durum, hata senaryoları.
 * AC-7: Boş/şekilsiz gövde → InvalidResponseError.
 * AC-S1: SessionExpiredError yukarı iletilir, yutulmaz.
 */

describe("fetchMe", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe("AC-7: apiFetch her ortamda kullanılır", () => {
    it("AC-7: valid response döner", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const validData = {
        user: { id: "user-123" },
        organizations: [{ id: "org-1", name: "Test Org" }],
        institutions: [],
      };
      vi.mocked(apiFetch).mockResolvedValueOnce(validData);

      const result = await fetchMe();

      expect(result).toEqual(validData);
      expect(isMeResponse(result)).toBe(true);
    });

    it("AC-7: apiFetch /me endpoint'ini çağırır", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const validData = {
        user: { id: "user-1" },
        organizations: [],
        institutions: [],
      };
      vi.mocked(apiFetch).mockResolvedValueOnce(validData);

      await fetchMe();

      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/me");
    });

    it("AC-7: undefined (204 No Content) → InvalidResponseError", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce(undefined);

      await expect(fetchMe()).rejects.toBeInstanceOf(InvalidResponseError);
    });

    it("AC-7: empty object {} → InvalidResponseError", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce({});

      await expect(fetchMe()).rejects.toBeInstanceOf(InvalidResponseError);
    });

    it("AC-7: null body → InvalidResponseError", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce(null);

      await expect(fetchMe()).rejects.toBeInstanceOf(InvalidResponseError);
    });

    it("AC-7: organizations undefined → InvalidResponseError", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce({
        user: { id: "user-1" },
        institutions: [],
      });

      await expect(fetchMe()).rejects.toBeInstanceOf(InvalidResponseError);
    });

    it("AC-7: organizations not array → InvalidResponseError", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce({
        user: { id: "user-1" },
        organizations: "not-an-array",
        institutions: [],
      });

      await expect(fetchMe()).rejects.toBeInstanceOf(InvalidResponseError);
    });

    it("AC-7: institutions not array → InvalidResponseError", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      vi.mocked(apiFetch).mockResolvedValueOnce({
        user: { id: "user-1" },
        organizations: [],
        institutions: { id: "1" },
      });

      await expect(fetchMe()).rejects.toBeInstanceOf(InvalidResponseError);
    });

    it("AC-7: talent_profile yokluğu geçerlidir (boş durum)", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const validData = {
        user: { id: "user-1" },
        organizations: [],
        institutions: [],
      };
      vi.mocked(apiFetch).mockResolvedValueOnce(validData);

      const result = await fetchMe();

      expect(isMeResponse(result)).toBe(true);
      expect(result).toEqual(validData);
    });

    it("AC-7: talent_profile null geçerlidir (boş durum)", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const validData = {
        user: { id: "user-1" },
        talent_profile: null,
        organizations: [],
        institutions: [],
      };
      vi.mocked(apiFetch).mockResolvedValueOnce(validData);

      const result = await fetchMe();

      expect(isMeResponse(result)).toBe(true);
    });
  });

  describe("AC-S1: Hatalar yukarı iletilir (yutulmaz)", () => {
    beforeEach(() => {
      vi.stubEnv("NODE_ENV", "production");
    });

    it("AC-S1: SessionExpiredError yukarı iletilir", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const error = new SessionExpiredError();
      vi.mocked(apiFetch).mockRejectedValueOnce(error);

      await expect(fetchMe()).rejects.toBeInstanceOf(SessionExpiredError);
    });

    it("AC-S1: NetworkError yukarı iletilir", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const error = new NetworkError("network");
      vi.mocked(apiFetch).mockRejectedValueOnce(error);

      await expect(fetchMe()).rejects.toBeInstanceOf(NetworkError);
    });

    it("AC-S1: ApiError yukarı iletilir", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const error = new ApiError({
        status: 401,
        code: "UNAUTHENTICATED",
        message: "Hata",
        requestId: "req-1",
      });
      vi.mocked(apiFetch).mockRejectedValueOnce(error);

      await expect(fetchMe()).rejects.toBeInstanceOf(ApiError);
    });

    it("AC-S1: Hatalar dönüştürülmez", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const originalError = new ApiError({
        status: 500,
        code: "INTERNAL",
        message: "Sunucu hatası",
        requestId: "req-err",
      });
      vi.mocked(apiFetch).mockRejectedValueOnce(originalError);

      try {
        await fetchMe();
      } catch (e) {
        expect(e).toBe(originalError);
      }
    });
  });

  describe("Davranış Sözleşmesi satır 1: Happy path", () => {
    beforeEach(() => {
      vi.stubEnv("NODE_ENV", "production");
    });

    it("Davranış 1: geçerli oturum → /me 200", async () => {
      const { apiFetch } = await import("@/lib/api/client");
      const data = {
        user: { id: "user-123", email: "user@test.com" },
        organizations: [{ id: "org-1", name: "Test" }],
        institutions: [],
      };
      vi.mocked(apiFetch).mockResolvedValueOnce(data);

      const result = await fetchMe();

      expect(result).toEqual(data);
      expect(isMeResponse(result)).toBe(true);
    });
  });
});
