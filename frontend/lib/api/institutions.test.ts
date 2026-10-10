import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getCoordinatorDashboard,
  requestInstitutionLink,
  approveLinkRequest,
  rejectLinkRequest,
  listPendingLinkRequests,
  listMyLinkRequests,
  inviteMember,
  createReminders,
  createInstitution,
  listInstitutionPartners,
  reportCsvUrl,
} from "./institutions";
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
  members: [
    { user_id: "user-10", email: "coordinator@test.com", role: "COORDINATOR", joined_at: "2026-01-15T00:00:00Z" },
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

  /**
   * YET-197/IS-10: Yeni link-request client fonksiyonları.
   */
  describe("requestInstitutionLink", () => {
    it("başarılı istek POST /institutions/{id}/link-requests çağırır", async () => {
      mockApiFetch.mockResolvedValueOnce(undefined);

      await requestInstitutionLink("inst-1");

      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/link-requests", { method: "POST" });
    });

    it("409 - zaten bekleyen talep varsa ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "HTTP_ERROR", message: "Pending link request already exists", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(requestInstitutionLink("inst-1")).rejects.toMatchObject({ status: 409 });
    });
  });

  describe("approveLinkRequest", () => {
    it("başarılı istek POST .../approve çağırır", async () => {
      mockApiFetch.mockResolvedValueOnce(undefined);

      await approveLinkRequest("inst-1", "req-1");

      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/link-requests/req-1/approve", { method: "POST" });
    });

    it("404 - yetkisiz/bulunamayan kurum için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "HTTP_ERROR", message: "Institution not found", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(approveLinkRequest("inst-b", "req-1")).rejects.toMatchObject({ status: 404 });
    });
  });

  describe("rejectLinkRequest", () => {
    it("başarılı istek POST .../reject çağırır", async () => {
      mockApiFetch.mockResolvedValueOnce(undefined);

      await rejectLinkRequest("inst-1", "req-1");

      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/link-requests/req-1/reject", { method: "POST" });
    });

    it("422 - zaten karar verilmiş talep için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "HTTP_ERROR", message: "Link request is not PENDING", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(rejectLinkRequest("inst-1", "req-1")).rejects.toMatchObject({ status: 422 });
    });
  });

  describe("listPendingLinkRequests", () => {
    it("happy path - items listesi döner", async () => {
      const response = {
        items: [
          { id: "req-1", talent_profile_id: "t-1", talent_full_name: "Ayşe Yılmaz", status: "PENDING", requested_at: "2026-10-01T00:00:00Z" },
        ],
      };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await listPendingLinkRequests("inst-1");

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/link-requests");
    });

    it("boş liste - 200 + items: []", async () => {
      mockApiFetch.mockResolvedValueOnce({ items: [] });

      const result = await listPendingLinkRequests("inst-1");

      expect(result?.items).toEqual([]);
    });

    it("404 - çapraz kiracı erişimi ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "HTTP_ERROR", message: "Institution not found", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(listPendingLinkRequests("inst-b")).rejects.toMatchObject({ status: 404 });
    });
  });

  describe("listMyLinkRequests", () => {
    it("happy path - talent'ın kendi geçmişi döner", async () => {
      const response = {
        items: [
          {
            id: "req-1",
            institution_id: "inst-1",
            institution_name: "Test Üniversitesi",
            status: "PENDING",
            requested_at: "2026-10-01T00:00:00Z",
            decided_at: null,
          },
        ],
      };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await listMyLinkRequests();

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/talents/me/institution-link-requests");
    });

    it("404 - talent profili yoksa ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "TALENT_PROFILE_NOT_FOUND", message: "Talent profili bulunamadı.", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(listMyLinkRequests()).rejects.toMatchObject({ status: 404, code: "TALENT_PROFILE_NOT_FOUND" });
    });

    it("401 - oturumsuz istek ApiError fırlatır", async () => {
      const error = new ApiError({ status: 401, code: "UNAUTHORIZED", message: "Kimlik doğrulama gerekli.", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(listMyLinkRequests()).rejects.toMatchObject({ status: 401 });
    });
  });

  /**
   * YET-202/ENT-01: Üye davet.
   */
  describe("inviteMember", () => {
    it("başarılı istek POST /institutions/{id}/members çağırır, 202 queued döner", async () => {
      mockApiFetch.mockResolvedValueOnce({ status: "queued" });

      const result = await inviteMember("inst-1", "aday@test.com", "COORDINATOR");

      expect(result).toEqual({ status: "queued" });
      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/members", {
        method: "POST",
        body: { email: "aday@test.com", role: "COORDINATOR" },
      });
    });

    it("ADMIN rolü ile de çağrılabilir", async () => {
      mockApiFetch.mockResolvedValueOnce({ status: "queued" });

      await inviteMember("inst-1", "yeni-admin@test.com", "ADMIN");

      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/members", {
        method: "POST",
        body: { email: "yeni-admin@test.com", role: "ADMIN" },
      });
    });

    it("404 - çağıran bu kurumun ADMIN'i değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "Institution not found", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(inviteMember("inst-b", "aday@test.com", "COORDINATOR")).rejects.toMatchObject({ status: 404 });
    });

    it("422 - geçersiz rol için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "INVALID_ROLE", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(
        inviteMember("inst-1", "aday@test.com", "COORDINATOR")
      ).rejects.toMatchObject({ status: 422, code: "INVALID_ROLE" });
    });
  });

  /**
   * YET-202/ENT-01: Toplu hatırlatma.
   */
  describe("createReminders", () => {
    it("başarılı istek POST /institutions/{id}/reminders çağırır, queued_count döner", async () => {
      mockApiFetch.mockResolvedValueOnce({ queued_count: 2 });

      const result = await createReminders("inst-1", ["eng-1", "eng-2"], "evaluation_pending");

      expect(result).toEqual({ queued_count: 2 });
      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/reminders", {
        method: "POST",
        body: { engagement_ids: ["eng-1", "eng-2"], template: "evaluation_pending" },
      });
    });

    it("404 - çağıran bu kurumun üyesi değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "Institution not found", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createReminders("inst-b", ["eng-1"], "evaluation_pending")).rejects.toMatchObject({ status: 404 });
    });

    it("422 - boş engagement_ids için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createReminders("inst-1", [], "evaluation_pending")).rejects.toMatchObject({ status: 422 });
    });
  });

  /**
   * YET-202/ENT-01: Kurum oluşturma.
   */
  describe("createInstitution", () => {
    it("happy path - POST /institutions/ çağırır (sondaki / ile, 307 redirect yok), 201 döner", async () => {
      const response = { id: "inst-1", name: "Test Üniversitesi", domain: null, verification_level: "T1", status: "ACTIVE" };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await createInstitution("Test Üniversitesi");

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/institutions/", {
        method: "POST",
        body: { name: "Test Üniversitesi" },
      });
    });

    it("domain alanı payload'da hiç yok (GUV-09 — backend yok sayıyor, göndermenin anlamı yok)", async () => {
      mockApiFetch.mockResolvedValueOnce({ id: "inst-2", name: "x", domain: null, verification_level: "T1", status: "ACTIVE" });

      await createInstitution("x");

      const call = mockApiFetch.mock.calls[0][1] as { body: Record<string, unknown> };
      expect(call.body).not.toHaveProperty("domain");
    });

    it("422 VALIDATION_ERROR - boş ad için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createInstitution("")).rejects.toMatchObject({ status: 422, code: "VALIDATION_ERROR" });
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(createInstitution("x")).rejects.toBeInstanceOf(NetworkError);
    });
  });
});

describe("listInstitutionPartners", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
  });

  it("GETs /institutions/{id}/partners and returns items", async () => {
    const payload = {
      items: [
        {
          organization_id: "org-1",
          organization_name: "Şişli Yazılım",
          verification_level: "T1",
          student_count: 2,
          engagement_count: 3,
          verified_count: 1,
        },
      ],
    };
    mockApiFetch.mockResolvedValueOnce(payload);

    const result = await listInstitutionPartners("inst-1");

    expect(mockApiFetch).toHaveBeenCalledWith("/institutions/inst-1/partners");
    expect(result).toEqual(payload);
  });

  it("propagates 404 for non-members", async () => {
    mockApiFetch.mockRejectedValueOnce(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "Kurum bulunamadı.", requestId: null })
    );
    await expect(listInstitutionPartners("inst-x")).rejects.toThrow(ApiError);
  });
});

describe("reportCsvUrl", () => {
  it("points at the report.csv endpoint of the institution", () => {
    expect(reportCsvUrl("inst-1")).toMatch(/\/institutions\/inst-1\/report\.csv$/);
  });

  it("encodes the id", () => {
    expect(reportCsvUrl("a/b")).toContain("/institutions/a%2Fb/report.csv");
  });
});
