import { describe, it, expect } from "vitest";
import {
  checkOrganizationDocument,
  rejectDocument,
  DOCUMENT_MAX_BYTES,
  USE_MOCK_DOCUMENT_CHECK,
} from "@/lib/api/organization-document";

function fileOf(type: string, size = 10): File {
  return new File([new Uint8Array(size)], "belge", { type });
}

/**
 * Belge kontrolü mock'tur (backend ucu yok): sonuç dosyaya değil formdaki beyana
 * bağlıdır ve deterministiktir. Tür/boyut ön kontrolü gerçektir.
 */
describe("organization-document (mock)", () => {
  it("mock bayrağı açık — gerçek uç gelene kadar bilinçli durum", () => {
    expect(USE_MOCK_DOCUMENT_CHECK).toBe(true);
  });

  it.each(["application/pdf", "image/png", "image/jpeg"])("izinli türü kabul eder: %s", (type) => {
    expect(rejectDocument(fileOf(type))).toBeNull();
  });

  it.each(["text/plain", "application/zip", "image/svg+xml", ""])("izinsiz türü reddeder: %s", (type) => {
    expect(rejectDocument(fileOf(type))).toBe("INVALID_TYPE");
  });

  it("5 MB sınırını uygular", () => {
    expect(rejectDocument(fileOf("application/pdf", DOCUMENT_MAX_BYTES))).toBeNull();
    expect(rejectDocument(fileOf("application/pdf", DOCUMENT_MAX_BYTES + 1))).toBe("TOO_LARGE");
  });

  it("kuruluş adı ve 16 haneli MERSİS varsa MATCH döner", async () => {
    const result = await checkOrganizationDocument(fileOf("application/pdf"), {
      entity_name: "Örnek A.Ş.",
      legal_id: "0123456789012345",
    });

    expect(result).toEqual({ status: "MATCH", qr_found: true, manual_review: false });
  });

  it.each([
    { entity_name: "", legal_id: "0123456789012345" },
    { entity_name: "Örnek A.Ş.", legal_id: "" },
    { entity_name: "Örnek A.Ş.", legal_id: "123" },
  ])("beyan eksikse UNVERIFIED + manuel inceleme döner: %o", async (claim) => {
    const result = await checkOrganizationDocument(fileOf("image/png"), claim);

    expect(result).toEqual({ status: "UNVERIFIED", qr_found: false, manual_review: true });
  });

  it("aynı girdi her zaman aynı sonucu verir (rastgelelik yok)", async () => {
    const claim = { entity_name: "Örnek A.Ş.", legal_id: "0123456789012345" };
    const results = await Promise.all(
      Array.from({ length: 5 }, () => checkOrganizationDocument(fileOf("application/pdf"), claim))
    );

    expect(new Set(results.map((r) => r.status))).toEqual(new Set(["MATCH"]));
  });
});
