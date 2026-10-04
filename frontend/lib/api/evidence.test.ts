import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { apiFetch } from "./client";
import {
  validateFile,
  requestUploadUrl,
  uploadFileToStorage,
  recordEvidence,
  listEvidenceForDeliverable,
} from "./evidence";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));

/**
 * PLAN 2.12 + YET-195: Kanıt yükleme API katmanı testleri — gerçek backend uçlarına
 * giden çağrılar (apiFetch / fetch sahte; ağ yok). Artık localStorage mock'u yok.
 */

function makeFile(content: string, name: string, type: string): File {
  return new File([content], name, { type });
}

describe("lib/api/evidence", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("validateFile", () => {
    it("PDF/JPEG/PNG/DOCX için ok:true ve doğru kind döner", () => {
      expect(validateFile(makeFile("x", "a.pdf", "application/pdf"))).toMatchObject({
        ok: true,
        kind: "DOCUMENT",
      });
      expect(validateFile(makeFile("x", "a.jpg", "image/jpeg"))).toMatchObject({
        ok: true,
        kind: "IMAGE",
      });
      expect(validateFile(makeFile("x", "a.png", "image/png"))).toMatchObject({
        ok: true,
        kind: "IMAGE",
      });
      expect(
        validateFile(
          makeFile(
            "x",
            "a.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          )
        )
      ).toMatchObject({ ok: true, kind: "DOCUMENT" });
    });

    it("desteklenmeyen içerik türü → dosya reddi (UNSUPPORTED_CONTENT_TYPE)", () => {
      const result = validateFile(makeFile("x", "a.exe", "application/x-msdownload"));
      expect(result).toMatchObject({ ok: false, code: "UNSUPPORTED_CONTENT_TYPE" });
    });

    it("10MB üstü dosya → dosya reddi (FILE_TOO_LARGE)", () => {
      const bigContent = "x".repeat(11 * 1024 * 1024);
      const result = validateFile(makeFile(bigContent, "a.pdf", "application/pdf"));
      expect(result).toMatchObject({ ok: false, code: "FILE_TOO_LARGE" });
    });
  });

  describe("requestUploadUrl", () => {
    it("POST /evidence/upload-url'i dosya adı, içerik türü ve boyutla çağırır", async () => {
      const file = makeFile("x", "resume.pdf", "application/pdf");
      const apiResponse = {
        upload_url: "http://minio/bucket",
        upload_fields: { key: "evidence/t/u.pdf" },
        object_key: "evidence/t/u.pdf",
        expires_in: 900,
      };
      vi.mocked(apiFetch).mockResolvedValueOnce(apiResponse);

      const response = await requestUploadUrl(file);

      expect(response).toEqual(apiResponse);
      expect(apiFetch).toHaveBeenCalledWith("/evidence/upload-url", {
        method: "POST",
        body: { filename: "resume.pdf", content_type: "application/pdf", size_bytes: 1 },
      });
    });

    it("boş yanıt → hata fırlatır", async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce(undefined);
      await expect(requestUploadUrl(makeFile("x", "a.pdf", "application/pdf"))).rejects.toThrow();
    });
  });

  describe("uploadFileToStorage", () => {
    it("alanları FormData'ya ekler, dosyayı EN SONA koyar ve POST eder", async () => {
      const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204 });
      vi.stubGlobal("fetch", fetchMock);
      const file = makeFile("x", "resume.pdf", "application/pdf");

      await uploadFileToStorage("http://minio/bucket", { key: "k", policy: "p" }, file);

      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("http://minio/bucket");
      expect(init.method).toBe("POST");
      const keys = Array.from((init.body as FormData).keys());
      expect(keys).toEqual(["key", "policy", "file"]);
    });

    it("depolama hata dönerse STORAGE_UPLOAD_FAILED fırlatır", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }));
      await expect(
        uploadFileToStorage("http://minio/bucket", {}, makeFile("x", "a.pdf", "application/pdf"))
      ).rejects.toMatchObject({ code: "STORAGE_UPLOAD_FAILED", status: 403 });
    });
  });

  describe("recordEvidence + listEvidenceForDeliverable", () => {
    const apiItem = {
      id: "ev-1",
      kind: "DOCUMENT",
      provenance: "SELF_UPLOADED",
      storage_key: "evidence/t/u.pdf",
      mime_type: "application/pdf",
      size_bytes: 1024,
      scan_status: "PENDING",
      deliverable_id: "del-1",
      created_at: "2026-10-02T00:00:00Z",
    };

    it("POST /evidence storage_key ile çağrılır ve object_key'e eşlenir", async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce(apiItem);

      const record = await recordEvidence({
        deliverable_id: "del-1",
        object_key: "evidence/t/u.pdf",
        kind: "DOCUMENT",
        mime_type: "application/pdf",
        size_bytes: 1024,
      });

      expect(apiFetch).toHaveBeenCalledWith("/evidence", {
        method: "POST",
        body: {
          storage_key: "evidence/t/u.pdf",
          kind: "DOCUMENT",
          mime_type: "application/pdf",
          size_bytes: 1024,
          deliverable_id: "del-1",
        },
      });
      expect(record.object_key).toBe("evidence/t/u.pdf");
      expect(record.scan_status).toBe("PENDING");
    });

    it("GET /evidence?deliverable_id= listeler ve scan_status'u olduğu gibi taşır", async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce([apiItem, { ...apiItem, id: "ev-2", scan_status: "FAILED" }]);

      const list = await listEvidenceForDeliverable("del 1");

      expect(apiFetch).toHaveBeenCalledWith("/evidence?deliverable_id=del%201");
      expect(list.map((e) => [e.id, e.scan_status])).toEqual([
        ["ev-1", "PENDING"],
        ["ev-2", "FAILED"],
      ]);
    });

    it("localStorage'a hiçbir şey yazmaz (ENT-02 kök nedeni)", async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce([apiItem]);
      await listEvidenceForDeliverable("del-1");
      expect(localStorage.length).toBe(0);
    });
  });
});
