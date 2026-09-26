import { describe, it, expect, vi, beforeEach } from "vitest";
import { getCoordinatorDashboard } from "./institutions";
import * as client from "./client";
import { ApiError, NetworkError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

const validDashboardResponse = {
  institution_id: "inst-1",
  summary: {
    pending_approval: 3,
    pending_evaluation: 7,
  },
  pending_approval: [
    {
      id: "eng-1",
      talent_id: "talent-1",
      organization_id: "org-1",
      title: "Yazılım Geliştirme Stajı",
      started_on: "2026-09-01",
    },
    {
      id: "eng-2",
      talent_id: "talent-2",
      organization_id: "org-2",
      title: "Veri Analiz Projesi",
      started_on: "2026-09-05",
    },
    {
      id: "eng-3",
      talent_id: "talent-3",
      organization_id: "org-1",
      title: "Sistem Admin Stajı",
      started_on: "2026-09-10",
    },
  ],
  pending_evaluation: [
    {
      id: "eng-4",
      talent_id: "talent-4",
      organization_id: "org-3",
      title: "Ürün Tasarım Projesi",
      ended_on: "2026-08-15",
    },
    {
      id: "eng-5",
      talent_id: "talent-5",
      organization_id: "org-1",
      title: "Finans Analizi",
      ended_on: "2026-08-20",
    },
    {
      id: "eng-6",
      talent_id: "talent-6",
      organization_id: "org-2",
      title: "Pazarlama Araştırması",
      ended_on: "2026-08-25",
    },
    {
      id: "eng-7",
      talent_id: "talent-7",
      organization_id: "org-4",
      title: "İnsan Kaynakları",
      ended_on: "2026-08-28",
    },
    {
      id: "eng-8",
      talent_id: "talent-8",
      organization_id: "org-1",
      title: "Muhasebe Stajı",
      ended_on: "2026-09-01",
    },
    {
      id: "eng-9",
      talent_id: "talent-9",
      organization_id: "org-3",
      title: "İş Analiz",
      ended_on: "2026-09-05",
    },
    {
      id: "eng-10",
      talent_id: "talent-10",
      organization_id: "org-2",
      title: "Yazılım Test",
      ended_on: "2026-09-08",
    },
  ],
};

/**
 * PLAN 3.9 (koordinator-dashboard-frontend) — API client testleri.
 * Mock apiFetch ile getCoordinatorDashboard fonksiyonunu test et.
 */
describe("lib/api/institutions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * AC-1: Happy path
   * Given: kendi kurumunda 3 PENDING_APPROVAL + 7 PENDING_EVALUATION
   * When: getCoordinatorDashboard çağrılır
   * Then: 200 + summary + iki liste döner
   */
  it("AC-1: happy path - summary ve iki liste ile 200 döner", async () => {
    mockApiFetch.mockResolvedValueOnce(validDashboardResponse);

    const result = await getCoordinatorDashboard("inst-1");

    expect(result).toEqual(validDashboardResponse);
    expect(result?.summary.pending_approval).toBe(3);
    expect(result?.summary.pending_evaluation).toBe(7);
    expect(result?.pending_approval).toHaveLength(3);
    expect(result?.pending_evaluation).toHaveLength(7);
    expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/dashboard");
  });

  /**
   * AC-2: Boş liste
   * Given: kurumda hiç bekleyen engagement yok
   * When: getCoordinatorDashboard çağrılır
   * Then: 200 + sıfır sayaçlar + boş listeler
   */
  it("AC-2: empty list - 200 ile sıfır sayaçlar ve boş listeler döner", async () => {
    const emptyResponse = {
      institution_id: "inst-2",
      summary: {
        pending_approval: 0,
        pending_evaluation: 0,
      },
      pending_approval: [],
      pending_evaluation: [],
    };
    mockApiFetch.mockResolvedValueOnce(emptyResponse);

    const result = await getCoordinatorDashboard("inst-2");

    expect(result?.summary.pending_approval).toBe(0);
    expect(result?.summary.pending_evaluation).toBe(0);
    expect(result?.pending_approval).toEqual([]);
    expect(result?.pending_evaluation).toEqual([]);
  });

  /**
   * AC-3: 404 - Kurum bulunamadı
   * Given: kullanıcı hiçbir kuruma üye değil veya backend 404 dönüyor
   * When: getCoordinatorDashboard çağrılır
   * Then: ApiError(404, "NOT_FOUND") fırlatılır
   */
  it("AC-3: 404 - Kurum bulunamadı hatasını tam eşleşmeyle döner", async () => {
    const apiError = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kurum bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(apiError);

    await expect(getCoordinatorDashboard("inst-nonexistent")).rejects.toMatchObject({
      status: 404,
      code: "NOT_FOUND",
    });
  });

  /**
   * AC-4: 401 - Oturumsuz istek
   * Given: kullanıcı oturum açmamış
   * When: getCoordinatorDashboard çağrılır
   * Then: ApiError(401, "UNAUTHENTICATED") fırlatılır
   */
  it("AC-4: 401 - UNAUTHENTICATED hatasını döner", async () => {
    const apiError = new ApiError({
      status: 401,
      code: "UNAUTHENTICATED",
      message: "Kimlik doğrulama gerekli.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(apiError);

    await expect(getCoordinatorDashboard("inst-1")).rejects.toMatchObject({
      status: 401,
      code: "UNAUTHENTICATED",
    });
  });

  /**
   * AC-5: Network/500 hatası
   * Given: ağ bağlantısı kopmuş veya backend 500 dönüyor
   * When: getCoordinatorDashboard çağrılır
   * Then: NetworkError veya ApiError(500) fırlatılır
   */
  it("AC-5: Network error - NetworkError('network') fırlatılır", async () => {
    const networkError = new NetworkError("network");
    mockApiFetch.mockRejectedValueOnce(networkError);

    await expect(getCoordinatorDashboard("inst-1")).rejects.toBeInstanceOf(NetworkError);
  });

  it("AC-5: Server error - ApiError(500) fırlatılır", async () => {
    const serverError = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-123",
    });
    mockApiFetch.mockRejectedValueOnce(serverError);

    await expect(getCoordinatorDashboard("inst-1")).rejects.toMatchObject({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
    });
  });

  /**
   * AC-7: XSS riski - title alanı serbest metni içerebilir
   * Given: title alanında HTML/script karakterleri var
   * When: getCoordinatorDashboard döner
   * Then: raw title döner (escape backend'de olur veya component'te), dangerouslySetInnerHTML kullanılmaz
   */
  it("AC-7: XSS riski - title alanı raw metni döner (component escape etmeli)", async () => {
    const xssResponse = {
      institution_id: "inst-1",
      summary: { pending_approval: 1, pending_evaluation: 0 },
      pending_approval: [
        {
          id: "eng-xss",
          talent_id: "t-1",
          organization_id: "o-1",
          title: "<script>alert('xss')</script> Stajı",
          started_on: "2026-09-01",
        },
      ],
      pending_evaluation: [],
    };
    mockApiFetch.mockResolvedValueOnce(xssResponse);

    const result = await getCoordinatorDashboard("inst-1");

    // API client ham title döner, escape component'te yapılır
    expect(result?.pending_approval[0].title).toBe("<script>alert('xss')</script> Stajı");
    expect(typeof result?.pending_approval[0].title).toBe("string");
  });

  /**
   * Cache key testi (AC-6/AC-S1)
   * Komponentin queryKey'de institutionId olmasını doğrulamak için
   * API client'in doğru parametreyi geçtiğini ve unique response döndüğünü test et
   */
  it("AC-6/AC-S1: Tenant isolation - farklı institution_id'ler ayrı çağrılar yapılır", async () => {
    const response1 = { ...validDashboardResponse, institution_id: "inst-1" };
    const response2 = {
      ...validDashboardResponse,
      institution_id: "inst-2",
      summary: { pending_approval: 2, pending_evaluation: 5 },
    };

    mockApiFetch.mockResolvedValueOnce(response1);
    const result1 = await getCoordinatorDashboard("inst-1");

    mockApiFetch.mockResolvedValueOnce(response2);
    const result2 = await getCoordinatorDashboard("inst-2");

    // Her institution_id için ayrı çağrı yapılmalı
    expect(mockApiFetch).toHaveBeenCalledTimes(2);
    expect(mockApiFetch).toHaveBeenNthCalledWith(1, "/institutions/inst-1/dashboard");
    expect(mockApiFetch).toHaveBeenNthCalledWith(2, "/institutions/inst-2/dashboard");

    // Sonuçlar farklı olmalı
    expect(result1?.institution_id).toBe("inst-1");
    expect(result2?.institution_id).toBe("inst-2");
    expect(result1?.summary.pending_evaluation).not.toBe(result2?.summary.pending_evaluation);
  });

  /**
   * Status kodu kesinlik testi
   * Davranış Sözleşmesi'ndeki status kodları tam eşleşmeyle doğrulanır
   */
  it("Davranış Sözleşmesi: 404 kodu tam olarak 404 olmalı", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kurum bulunamadı.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await getCoordinatorDashboard("inst-404");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(404); // Tam eşleşme, 403 değil
        expect(err.code).toBe("NOT_FOUND");
      }
    }
  });

  it("Davranış Sözleşmesi: 401 kodu tam olarak 401 olmalı", async () => {
    const error = new ApiError({
      status: 401,
      code: "UNAUTHENTICATED",
      message: "Kimlik doğrulama gerekli.",
      requestId: null,
    });
    mockApiFetch.mockRejectedValueOnce(error);

    try {
      await getCoordinatorDashboard("inst-1");
      expect.fail("Should have thrown");
    } catch (err) {
      if (err instanceof ApiError) {
        expect(err.status).toBe(401); // Tam eşleşme
        expect(err.code).toBe("UNAUTHENTICATED");
      }
    }
  });
});
