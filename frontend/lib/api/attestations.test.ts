import { describe, it, expect, vi, beforeEach } from "vitest";
import { createAttestation, revokeAttestation } from "./attestations";
import * as client from "./client";
import { ApiError, NetworkError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

describe("lib/api/attestations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createAttestation", () => {
    it("happy path - downgrade yok, 201 yanıtını döner", async () => {
      const response = { id: "att-1", claim_type: "COMPETENCE", requested_claim_type: "COMPETENCE", downgrade_reasons: [] };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await createAttestation("eng-1", { claim_type: "COMPETENCE", version: 3, skill_id: "skill-1" });

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/attestations", {
        method: "POST",
        body: { claim_type: "COMPETENCE", version: 3, skill_id: "skill-1" },
      });
    });

    it("downgrade VAR - 201 olarak döner, hata fırlatmaz", async () => {
      const response = { id: "att-2", claim_type: "PARTICIPATION", requested_claim_type: "COMPETENCE", downgrade_reasons: ["NO_DELIVERABLE"] };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await createAttestation("eng-1", { claim_type: "COMPETENCE", version: 1 });

      expect(result.claim_type).toBe("PARTICIPATION");
      expect(result.downgrade_reasons).toEqual(["NO_DELIVERABLE"]);
    });

    it("403 FORBIDDEN - TALENT kendi engagement'ına tanıklık edemez", async () => {
      const error = new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createAttestation("eng-1", { claim_type: "COMPETENCE", version: 1 })).rejects.toMatchObject({ status: 403 });
    });

    it("409 INVALID_STATE_TRANSITION - EVALUATED değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "INVALID_STATE_TRANSITION", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createAttestation("eng-1", { claim_type: "COMPETENCE", version: 1 })).rejects.toMatchObject({ code: "INVALID_STATE_TRANSITION" });
    });

    it("409 CONFLICT - sürüm uyuşmazlığında ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "CONFLICT", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createAttestation("eng-1", { claim_type: "COMPETENCE", version: 1 })).rejects.toMatchObject({ code: "CONFLICT" });
    });

    it("409 SELF_ATTESTATION_FORBIDDEN - kendi deneyimine tanıklıkta ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "SELF_ATTESTATION_FORBIDDEN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createAttestation("eng-1", { claim_type: "COMPETENCE", version: 1 })).rejects.toMatchObject({ code: "SELF_ATTESTATION_FORBIDDEN" });
    });

    it("409 ATTESTATION_ALREADY_EXISTS - tekrar tanıklıkta ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "ATTESTATION_ALREADY_EXISTS", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createAttestation("eng-1", { claim_type: "COMPETENCE", version: 1 })).rejects.toMatchObject({ code: "ATTESTATION_ALREADY_EXISTS" });
    });

    it("404 NOT_FOUND - kapsam dışı engagement için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createAttestation("eng-missing", { claim_type: "COMPETENCE", version: 1 })).rejects.toMatchObject({ status: 404 });
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(createAttestation("eng-1", { claim_type: "COMPETENCE", version: 1 })).rejects.toBeInstanceOf(NetworkError);
    });
  });

  /**
   * YET-202/ENT-01: Tanıklık geri çekme.
   */
  describe("revokeAttestation", () => {
    it("happy path - POST /attestations/{id}/revoke çağırır, 200 döner", async () => {
      const response = { id: "att-1", revoked_at: "2026-10-05T10:00:00Z", revoke_reason: "Yanlış girilmiş" };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await revokeAttestation("att-1", "Yanlış girilmiş");

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/attestations/att-1/revoke", {
        method: "POST",
        body: { revoke_reason: "Yanlış girilmiş" },
      });
    });

    it("403 FORBIDDEN - attestor değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(revokeAttestation("att-1", "gerekçe")).rejects.toMatchObject({ status: 403 });
    });

    it("409 ALREADY_REVOKED - zaten geri çekilmişse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "ALREADY_REVOKED", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(revokeAttestation("att-1", "gerekçe")).rejects.toMatchObject({ code: "ALREADY_REVOKED" });
    });

    it("404 NOT_FOUND - kapsam dışı attestation için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(revokeAttestation("att-missing", "gerekçe")).rejects.toMatchObject({ status: 404 });
    });

    it("422 VALIDATION_ERROR - boş gerekçe için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(revokeAttestation("att-1", "")).rejects.toMatchObject({ status: 422, code: "VALIDATION_ERROR" });
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(revokeAttestation("att-1", "gerekçe")).rejects.toBeInstanceOf(NetworkError);
    });
  });
});
