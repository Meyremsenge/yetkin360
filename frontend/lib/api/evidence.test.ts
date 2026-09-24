import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  validateFile,
  requestUploadUrl,
  uploadFileToStorage,
  recordEvidence,
  listEvidenceForDeliverable,
} from "./evidence";

/**
 * PLAN 2.12: Kanıt (evidence) yükleme mock katmanı testleri.
 * Store localStorage'da tutulduğu için her testte sıfırlanır.
 */

function makeFile(content: string, name: string, type: string): File {
  return new File([content], name, { type });
}

describe("lib/api/evidence", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useRealTimers();
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

  describe("requestUploadUrl + uploadFileToStorage (mock)", () => {
    it("upload_url/upload_fields/object_key/expires_in şeklinde bir yanıt döner", async () => {
      const file = makeFile("x", "resume.pdf", "application/pdf");
      const response = await requestUploadUrl(file);

      expect(response.upload_url).toBeTruthy();
      expect(response.object_key).toContain("evidence/");
      expect(response.expires_in).toBe(900);
      expect(typeof response.upload_fields).toBe("object");
    });

    it("depolamaya yükleme hatasız tamamlanır", async () => {
      const file = makeFile("x", "resume.pdf", "application/pdf");
      const response = await requestUploadUrl(file);

      await expect(
        uploadFileToStorage(response.upload_url, response.upload_fields, file)
      ).resolves.toBeUndefined();
    });
  });

  describe("recordEvidence + listEvidenceForDeliverable (mock, localStorage)", () => {
    it("kayıt scan_status=PENDING ile oluşturulur ve deliverable'a göre filtrelenir", async () => {
      const record = await recordEvidence({
        deliverable_id: "del-1",
        object_key: "evidence/x/y.pdf",
        kind: "DOCUMENT",
        mime_type: "application/pdf",
        size_bytes: 1024,
      });

      expect(record.scan_status).toBe("PENDING");
      expect(record.deliverable_id).toBe("del-1");

      const listForDel1 = await listEvidenceForDeliverable("del-1");
      expect(listForDel1).toHaveLength(1);
      expect(listForDel1[0].id).toBe(record.id);

      const listForOtherDel = await listEvidenceForDeliverable("del-2");
      expect(listForOtherDel).toHaveLength(0);
    });

    it("kalıcılık: yeniden okununca da kayıt localStorage'dan gelir", async () => {
      await recordEvidence({
        deliverable_id: "del-1",
        object_key: "evidence/x/y.pdf",
        kind: "DOCUMENT",
        mime_type: "application/pdf",
        size_bytes: 1024,
      });

      const reread = await listEvidenceForDeliverable("del-1");
      expect(reread).toHaveLength(1);
    });

    it("bir süre sonra scan_status PENDING'den CLEAN'e döner (mock tarama simülasyonu, deterministik)", async () => {
      vi.useFakeTimers();

      // recordEvidence() içindeki delay(300) de fake timer'a bağlı — önce onu ilerletip
      // sonucu alıyoruz, sonra tarama simülasyonunun setTimeout(4000)'ini ilerletiyoruz.
      const recordPromise = recordEvidence({
        deliverable_id: "del-1",
        object_key: "evidence/x/y.pdf",
        kind: "DOCUMENT",
        mime_type: "application/pdf",
        size_bytes: 1024,
      });
      await vi.advanceTimersByTimeAsync(300);
      const record = await recordPromise;
      expect(record.scan_status).toBe("PENDING");

      await vi.advanceTimersByTimeAsync(4000);

      const [resolved] = await listEvidenceForDeliverable("del-1");
      expect(resolved.scan_status).toBe("CLEAN");

      vi.useRealTimers();
    });
  });
});
