import { describe, it, expect, vi, beforeEach } from "vitest";
import * as admin from "./admin";
import * as client from "./client";
import { ApiError, NetworkError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

/**
 * PLAN 3.6 — Admin ekranları (kurum doğrulama + skill yönetimi).
 * Admin API client fonksiyonlarının unit testleri.
 */

// ============================================================================
// Mock veri — Backend response şemalarından
// ============================================================================

const mockOrganization = {
  id: "org-1",
  name: "Tech Startup Inc.",
  legal_id: "TR123456789",
  domain: "techstartup.com",
  verification_level: "T2",
  verified_at: "2026-09-27T10:00:00Z",
  created_at: "2026-09-20T00:00:00Z",
};

const mockOrganizationWithNulls = {
  id: "org-2",
  name: "Startup Inc.",
  legal_id: null,
  domain: null,
  verification_level: "T0",
  verified_at: null,
  created_at: "2026-09-21T00:00:00Z",
};

const mockVerificationQueue = {
  items: [mockOrganization, mockOrganizationWithNulls],
  limit: 50,
  offset: 0,
  has_more: false,
};

const mockEmptyQueue = { items: [], limit: 50, offset: 0, has_more: false };

const mockSkill = {
  id: "skill-1",
  slug: "python",
  name_tr: "Python",
  name_en: "Python",
  category: "LANGUAGE",
  parent_id: null,
  status: "ACTIVE",
  merged_into_id: null,
  created_at: "2026-09-01T00:00:00Z",
};

const mockSkillWithNulls = {
  id: "skill-2",
  slug: "web-dev",
  name_tr: "Web Geliştirme",
  name_en: null,
  category: "DOMAIN",
  parent_id: "skill-1",
  status: "ACTIVE",
  merged_into_id: null,
  created_at: "2026-09-05T00:00:00Z",
};

const mockDeprecatedSkill = {
  id: "skill-3",
  slug: "flash",
  name_tr: "Flash",
  name_en: "Flash",
  category: "LANGUAGE",
  parent_id: null,
  status: "DEPRECATED",
  merged_into_id: null,
  created_at: "2025-01-01T00:00:00Z",
};

const mockMergedSkill = {
  id: "skill-4",
  slug: "js",
  name_tr: "JavaScript",
  name_en: "JavaScript",
  category: "LANGUAGE",
  parent_id: null,
  status: "MERGED",
  merged_into_id: "skill-1",
  created_at: "2026-01-01T00:00:00Z",
};

// ============================================================================
// getVerificationQueue — AC-1, AC-4, AC-8
// ============================================================================

describe("lib/api/admin — getVerificationQueue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * AC-1: Happy path — kuyruk dolu, her kurum alanı var
   */
  it("AC-1: dolu kuyruk — 200 ile items döner", async () => {
    mockApiFetch.mockResolvedValueOnce(mockVerificationQueue);

    const result = await admin.getVerificationQueue();

    expect(result).toEqual(mockVerificationQueue);
    expect(result?.items).toHaveLength(2);
    expect(result?.items[0].name).toBe("Tech Startup Inc.");
  });

  /**
   * AC-4: Boş kuyruk — 200 ile empty items döner
   */
  it("AC-4: boş kuyruk — 200 ile items:[] döner", async () => {
    mockApiFetch.mockResolvedValueOnce(mockEmptyQueue);

    const result = await admin.getVerificationQueue();

    expect(result?.items).toEqual([]);
    expect(result?.items).toHaveLength(0);
  });

  /**
   * AC-8: Dış bağımlılık hatası — 500 döner
   */
  it("AC-8: server error — ApiError(500) fırlatılır", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-123",
    });
    mockApiFetch.mockRejectedValueOnce(error);

    await expect(admin.getVerificationQueue()).rejects.toMatchObject({
      status: 500,
    });
  });

  /**
   * AC-8: Zaman aşımı — NetworkError("timeout") fırlatılır
   */
  it("AC-8: timeout — NetworkError('timeout') fırlatılır", async () => {
    const error = new NetworkError("timeout");
    mockApiFetch.mockRejectedValueOnce(error);

    await expect(admin.getVerificationQueue()).rejects.toBeInstanceOf(NetworkError);
  });

  /**
   * AC-9/AC-S2: Admin olmayan kullanıcı — 404 döner (var/yok ayrımı yok)
   */
  it("AC-9/AC-S2: yetkisiz erişim — 404 TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.getVerificationQueue();
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404); // Tam eşleşme, 403 değil
        expect(err.code).toBe("NOT_FOUND");
      }
    }
  });
});

// ============================================================================
// updateVerificationLevel — AC-2, AC-3, AC-8, AC-9
// ============================================================================

describe("lib/api/admin — updateVerificationLevel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * AC-2: Happy path — seviye güncelleme başarılı
   */
  it("AC-2: happy path — POST /admin/organizations/{id}/verification-level 200 döner", async () => {
    const updated = {
      ...mockOrganization,
      verification_level: "T3",
      verified_at: "2026-09-27T11:00:00Z",
    };
    mockApiFetch.mockResolvedValueOnce(updated);

    const result = await admin.updateVerificationLevel("org-1", "T3");

    expect(result?.verification_level).toBe("T3");
    expect(result?.verified_at).toBe("2026-09-27T11:00:00Z");
  });

  /**
   * AC-3: Kaynak yok — 404 "Kurum bulunamadı."
   */
  it("AC-3: kaynak yok — 404 'Kurum bulunamadı.' TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kurum bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.updateVerificationLevel("org-nonexistent", "T3");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404); // Tam eşleşme
        expect(err.message).toBe("Kurum bulunamadı.");
      }
    }
  });

  /**
   * AC-2: Girdi geçersiz — 422 (enum dışı level)
   */
  it("AC-2: girdi geçersiz — 422 Unprocessable Entity döner", async () => {
    const error = new ApiError({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Geçersiz verification_level.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.updateVerificationLevel("org-1", "INVALID_LEVEL");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(422);
      }
    }
  });

  /**
   * AC-8: Dış bağımlılık hatası — 500
   */
  it("AC-8: server error — ApiError(500) fırlatılır", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-456",
    });
    mockApiFetch.mockRejectedValueOnce(error);

    await expect(admin.updateVerificationLevel("org-1", "T3")).rejects.toMatchObject({
      status: 500,
    });
  });

  /**
   * AC-9/AC-S2: Admin olmayan kullanıcı — 404 (var/yok ayrımı yok)
   */
  it("AC-9/AC-S2: yetkisiz erişim — 404 TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.updateVerificationLevel("org-1", "T3");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404); // Tam eşleşme, 403 değil
      }
    }
  });
});

// ============================================================================
// createSkill — AC-5, AC-6, AC-8, AC-9
// ============================================================================

describe("lib/api/admin — createSkill", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * AC-5: Happy path — skill oluştur başarılı, 201
   */
  it("AC-5: happy path — POST /admin/skills 201 döner", async () => {
    mockApiFetch.mockResolvedValueOnce(mockSkill);

    const result = await admin.createSkill("python", "Python", "LANGUAGE");

    expect(result?.slug).toBe("python");
    expect(result?.name_tr).toBe("Python");
    expect(result?.status).toBe("ACTIVE");
  });

  /**
   * AC-6: Slug çakışması — 409 CONFLICT
   */
  it("AC-6: slug çakışması — 409 CONFLICT TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 409,
      code: "CONFLICT",
      message: "Bu slug zaten kullanımda.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.createSkill("python", "Pythonnn", "LANGUAGE");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(409); // Tam eşleşme
        expect(err.code).toBe("CONFLICT");
        expect(err.message).toBe("Bu slug zaten kullanımda.");
      }
    }
  });

  /**
   * AC-8: Server error — 500
   */
  it("AC-8: server error — ApiError(500) fırlatılır", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-789",
    });
    mockApiFetch.mockRejectedValueOnce(error);

    await expect(admin.createSkill("python", "Python", "LANGUAGE")).rejects.toMatchObject({
      status: 500,
    });
  });

  /**
   * AC-9/AC-S2: Admin olmayan kullanıcı — 404
   */
  it("AC-9/AC-S2: yetkisiz erişim — 404 TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.createSkill("python", "Python", "LANGUAGE");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404); // Tam eşleşme, 403 değil
      }
    }
  });

  /**
   * Nullable alan testi — name_en null gelirse uygulanır
   */
  it("Nullable alan — name_en null ise uygulanır", async () => {
    mockApiFetch.mockResolvedValueOnce(mockSkillWithNulls);

    const result = await admin.createSkill("web-dev", "Web Geliştirme", "DOMAIN");

    expect(result?.name_en).toBeNull();
    expect(result?.name_tr).toBe("Web Geliştirme");
  });

  /**
   * Nullable alan testi — parent_id null ise "Kök seviye"
   */
  it("Nullable alan — parent_id null ise kök seviye işlenir", async () => {
    mockApiFetch.mockResolvedValueOnce(mockSkill);

    const result = await admin.createSkill("python", "Python", "LANGUAGE");

    expect(result?.parent_id).toBeNull();
    // UI'da "Kök seviye" gösterilir
  });
});

// ============================================================================
// updateSkill — AC-7, AC-8, AC-9
// ============================================================================

describe("lib/api/admin — updateSkill", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * AC-7: Skill güncelle — 200
   */
  it("AC-7: skill güncelle — PATCH /admin/skills/{id} 200 döner", async () => {
    const updated = { ...mockSkill, name_tr: "Python 3" };
    mockApiFetch.mockResolvedValueOnce(updated);

    const result = await admin.updateSkill("skill-1", "Python 3");

    expect(result?.name_tr).toBe("Python 3");
  });

  /**
   * AC-9/AC-S2: Admin olmayan kullanıcı — 404
   */
  it("AC-9/AC-S2: yetkisiz erişim — 404 TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.updateSkill("skill-1", "Python 3");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404);
      }
    }
  });

  /**
   * Kaynak yok — skill silinmiş/yanlış id
   */
  it("Kaynak yok — 404 döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Yetkinlik bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.updateSkill("skill-nonexistent", "Python 3");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404);
        expect(err.message).toBe("Yetkinlik bulunamadı.");
      }
    }
  });
});

// ============================================================================
// deprecateSkill — AC-7, AC-8, AC-9
// ============================================================================

describe("lib/api/admin — deprecateSkill", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * AC-7: Skill deprecate — 200
   */
  it("AC-7: skill deprecate — POST /admin/skills/{id}/deprecate 200 döner", async () => {
    mockApiFetch.mockResolvedValueOnce(mockDeprecatedSkill);

    const result = await admin.deprecateSkill("skill-3");

    expect(result?.status).toBe("DEPRECATED");
  });

  /**
   * AC-8: Server error — 500
   */
  it("AC-8: server error — ApiError(500) fırlatılır", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-999",
    });
    mockApiFetch.mockRejectedValueOnce(error);

    await expect(admin.deprecateSkill("skill-1")).rejects.toMatchObject({
      status: 500,
    });
  });

  /**
   * AC-9/AC-S2: Admin olmayan kullanıcı — 404
   */
  it("AC-9/AC-S2: yetkisiz erişim — 404 TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.deprecateSkill("skill-1");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404);
      }
    }
  });
});

// ============================================================================
// mergeSkill — AC-7, AC-8, AC-9
// ============================================================================

describe("lib/api/admin — mergeSkill", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * AC-7: Skill merge — 200
   */
  it("AC-7: skill merge — POST /admin/skills/{id}/merge 200 döner", async () => {
    mockApiFetch.mockResolvedValueOnce(mockMergedSkill);

    const result = await admin.mergeSkill("skill-4", "skill-1");

    expect(result?.status).toBe("MERGED");
    expect(result?.merged_into_id).toBe("skill-1");
  });

  /**
   * AC-8: Server error — 500
   */
  it("AC-8: server error — ApiError(500) fırlatılır", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-111",
    });
    mockApiFetch.mockRejectedValueOnce(error);

    await expect(admin.mergeSkill("skill-4", "skill-1")).rejects.toMatchObject({
      status: 500,
    });
  });

  /**
   * AC-9/AC-S2: Admin olmayan kullanıcı — 404
   */
  it("AC-9/AC-S2: yetkisiz erişim — 404 TAM EŞLEŞMEYLE döner", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await admin.mergeSkill("skill-4", "skill-1");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404);
      }
    }
  });

  /**
   * Nullable alan testi — merged_into_id TAM dolu olmalı (backend garantisi)
   */
  it("Nullable alan — MERGED durumunda merged_into_id TAM dolu olmalı", async () => {
    mockApiFetch.mockResolvedValueOnce(mockMergedSkill);

    const result = await admin.mergeSkill("skill-4", "skill-1");

    expect(result?.status).toBe("MERGED");
    expect(result?.merged_into_id).not.toBeNull();
    expect(result?.merged_into_id).toBe("skill-1");
  });
});

// ============================================================================
// Status kodu kesinlik testleri — Davranış Sözleşmesi
// ============================================================================

describe("Davranış Sözleşmesi — Status kod tam eşleşmeleri", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("404 kodu TAM OLARAK 404 olmalı, 403 değil", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await client.apiFetch("/admin/verification-queue");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404);
        expect(err.status).not.toBe(403);
      }
    }
  });

  it("409 kodu TAM OLARAK 409 olmalı", async () => {
    const error = new ApiError({
      status: 409,
      code: "CONFLICT",
      message: "Bu slug zaten kullanımda.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await client.apiFetch("/admin/skills", {
        method: "POST",
        body: { slug: "python" },
      });
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(409);
      }
    }
  });

  it("422 kodu TAM OLARAK 422 olmalı", async () => {
    const error = new ApiError({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Geçersiz alan.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await client.apiFetch("/admin/organizations/org-1/verification-level", {
        method: "POST",
        body: { verification_level: "INVALID" },
      });
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(422);
      }
    }
  });

  it("500 kodu TAM OLARAK 500 olmalı", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-123",
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await client.apiFetch("/admin/verification-queue");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(500);
      }
    }
  });
});

// ============================================================================
// admin-sayfalama-ve-kabuk — limit/offset + has_more zarfı
// ============================================================================

describe("lib/api/admin — sayfalama", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getVerificationQueue/getSkills/getFraudQueue limit ve offset'i sorguya yazar", async () => {
    mockApiFetch.mockResolvedValue({ items: [], limit: 50, offset: 100, has_more: false });

    await admin.getVerificationQueue({ limit: 50, offset: 100 });
    await admin.getSkills({ limit: 200, offset: 200 });
    await admin.getFraudQueue({ offset: 50 });

    expect(mockApiFetch).toHaveBeenNthCalledWith(1, "/admin/verification-queue?limit=50&offset=100");
    expect(mockApiFetch).toHaveBeenNthCalledWith(2, "/admin/skills?limit=200&offset=200");
    expect(mockApiFetch).toHaveBeenNthCalledWith(3, "/admin/fraud-queue?limit=50&offset=50");
  });

  it("varsayılan: limit=50, offset=0", async () => {
    mockApiFetch.mockResolvedValue({ items: [], limit: 50, offset: 0, has_more: false });

    await admin.getVerificationQueue();

    expect(mockApiFetch).toHaveBeenCalledWith("/admin/verification-queue?limit=50&offset=0");
  });

  it("getAllSkills has_more=false olana kadar tüm sayfaları dolaşır", async () => {
    const a = { id: "1" };
    const b = { id: "2" };
    mockApiFetch
      .mockResolvedValueOnce({ items: [a], limit: 200, offset: 0, has_more: true })
      .mockResolvedValueOnce({ items: [b], limit: 200, offset: 1, has_more: false });

    const all = await admin.getAllSkills();

    expect(all).toEqual([a, b]);
    expect(mockApiFetch).toHaveBeenNthCalledWith(2, "/admin/skills?limit=200&offset=1");
  });

  it("getAllSkills bir sayfa hata verirse kısmi liste dönmez, reddeder", async () => {
    mockApiFetch
      .mockResolvedValueOnce({ items: [{ id: "1" }], limit: 200, offset: 0, has_more: true })
      .mockRejectedValueOnce(new NetworkError("timeout"));

    await expect(admin.getAllSkills()).rejects.toBeInstanceOf(NetworkError);
  });
});
