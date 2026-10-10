import { describe, it, expect, vi, beforeEach } from "vitest";
import { createOrganization, getOrganization, inviteOrgMember, verifyDomain, listOrganizationDirectory } from "./organizations";
import * as client from "./client";
import { ApiError, NetworkError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

describe("lib/api/organizations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createOrganization", () => {
    it("happy path - POST /organizations çağırır, 201 döner", async () => {
      const response = {
        id: "org-1", name: "Acme A.Ş.", domain: "acme.com", legal_id: "ORG-1",
        verification_level: "T1", status: "ACTIVE",
      };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await createOrganization({ name: "Acme A.Ş.", domain: "acme.com", legal_id: "ORG-1" });

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/", {
        method: "POST",
        body: { name: "Acme A.Ş.", domain: "acme.com", legal_id: "ORG-1" },
      });
    });

    it("domain ve legal_id opsiyonel - olmadan çağrılabilir", async () => {
      const response = { id: "org-2", name: "Küçük Org", domain: null, legal_id: null, verification_level: "T1", status: "ACTIVE" };
      mockApiFetch.mockResolvedValueOnce(response);

      await createOrganization({ name: "Küçük Org" });

      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/", {
        method: "POST",
        body: { name: "Küçük Org" },
      });
    });

    it("409 LEGAL_ID_TAKEN - tekrar eden sicil no için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "LEGAL_ID_TAKEN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createOrganization({ name: "x", legal_id: "DUP-1" })).rejects.toMatchObject({ status: 409, code: "LEGAL_ID_TAKEN" });
    });

    it("422 VALIDATION_ERROR - geçersiz ad/domain için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createOrganization({ name: "" })).rejects.toMatchObject({ status: 422, code: "VALIDATION_ERROR" });
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(createOrganization({ name: "x" })).rejects.toBeInstanceOf(NetworkError);
    });
  });

  describe("getOrganization", () => {
    it("happy path - GET /organizations/{id} çağırır", async () => {
      const response = { id: "org-1", name: "Acme", domain: "acme.com", legal_id: null, verification_level: "T2", status: "ACTIVE" };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await getOrganization("org-1");

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/org-1");
    });

    it("404 - kapsam dışı organizasyon için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(getOrganization("org-other")).rejects.toMatchObject({ status: 404 });
    });
  });

  describe("inviteOrgMember", () => {
    it("happy path - POST /organizations/{id}/members çağırır, 202 queued döner", async () => {
      mockApiFetch.mockResolvedValueOnce({ status: "queued" });

      const result = await inviteOrgMember("org-1", "aday@test.com", "MEMBER");

      expect(result).toEqual({ status: "queued" });
      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/org-1/members", {
        method: "POST",
        body: { email: "aday@test.com", role: "MEMBER" },
      });
    });

    it("ADMIN rolü ile de çağrılabilir", async () => {
      mockApiFetch.mockResolvedValueOnce({ status: "queued" });

      await inviteOrgMember("org-1", "yeni-admin@test.com", "ADMIN");

      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/org-1/members", {
        method: "POST",
        body: { email: "yeni-admin@test.com", role: "ADMIN" },
      });
    });

    it("404 - çağıran bu organizasyonun ADMIN'i değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(inviteOrgMember("org-b", "x@test.com", "MEMBER")).rejects.toMatchObject({ status: 404 });
    });

    it("422 INVALID_ROLE - geçersiz rol için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "INVALID_ROLE", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(inviteOrgMember("org-1", "x@test.com", "MEMBER")).rejects.toMatchObject({ code: "INVALID_ROLE" });
    });
  });

  describe("verifyDomain", () => {
    it("happy path (pending) - POST /organizations/{id}/verify-domain çağırır, body göndermez", async () => {
      const response = { dns_txt_record: "yetkin360_verify_abc123", status: "pending" as const };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await verifyDomain("org-1");

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/org-1/verify-domain", { method: "POST" });
    });

    it("happy path (verified) - status verified döner", async () => {
      const response = { dns_txt_record: "yetkin360_verify_abc123", status: "verified" as const };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await verifyDomain("org-1");

      expect(result.status).toBe("verified");
    });

    it("400 FREE_EMAIL_DOMAIN - ücretsiz e-posta sağlayıcısı için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 400, code: "FREE_EMAIL_DOMAIN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(verifyDomain("org-1")).rejects.toMatchObject({ status: 400, code: "FREE_EMAIL_DOMAIN" });
    });

    it("409 DOMAIN_ALREADY_VERIFIED - başka organizasyonda doğrulanmışsa ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "DOMAIN_ALREADY_VERIFIED", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(verifyDomain("org-1")).rejects.toMatchObject({ code: "DOMAIN_ALREADY_VERIFIED" });
    });

    it("429 TOO_MANY_REQUESTS - rate limit için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 429, code: "TOO_MANY_REQUESTS", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(verifyDomain("org-1")).rejects.toMatchObject({ status: 429, code: "TOO_MANY_REQUESTS" });
    });

    it("404 - çağıran ADMIN değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(verifyDomain("org-b")).rejects.toMatchObject({ status: 404 });
    });
  });

  describe("listOrganizationDirectory", () => {
    it("happy path - GET /organizations/ çağırır, items döner", async () => {
      const items = [
        { id: "org-1", name: "Acme A.Ş.", domain: "acme.com", verification_level: "T2" },
      ];
      mockApiFetch.mockResolvedValueOnce({ items });

      const result = await listOrganizationDirectory();

      expect(result).toEqual(items);
      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/");
    });

    it("arama terimi verildiğinde q query param'ı eklenir", async () => {
      mockApiFetch.mockResolvedValueOnce({ items: [] });

      await listOrganizationDirectory("Acme & Co");

      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/?q=Acme%20%26%20Co");
    });

    it("boş/whitespace arama terimi query param eklemez", async () => {
      mockApiFetch.mockResolvedValueOnce({ items: [] });

      await listOrganizationDirectory("   ");

      expect(mockApiFetch).toHaveBeenCalledWith("/organizations/");
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(listOrganizationDirectory()).rejects.toBeInstanceOf(NetworkError);
    });
  });
});
