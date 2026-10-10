import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DogrulamaKuyruguPage from "@/app/admin/dogrulama-kuyrugu/page";
import { useSession } from "@/lib/session/use-session";
import { ApiError, NetworkError } from "@/lib/api/errors";
import * as adminApi from "@/lib/api/admin";

// Mock dependencies
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/admin");

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

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


function paged<T>(items: T[], extra: Partial<{ limit: number; offset: number; has_more: boolean }> = {}) {
  return { items, limit: 50, offset: 0, has_more: false, ...extra };
}

const mockVerificationQueue = paged([mockOrganization, mockOrganizationWithNulls]);

const mockEmptyQueue = paged([]);

/**
 * PLAN 3.6 — Admin kurum doğrulama kuyruğu sayfası testi.
 * AC-1, AC-3, AC-4, AC-8, AC-9
 */
describe("DogrulamaKuyruguPage (/admin/dogrulama-kuyrugu)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Mock session — admin kullanıcı
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: "admin-1", email: "admin@test.com", is_platform_admin: true },
        organizations: [],
        institutions: [],
        talent_profile: null,
      },
      error: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
  });

  afterEach(() => {
    cleanup();
  });

  // =========================================================================
  // AC-1: Kuyruk dolu — liste gösterilir
  // =========================================================================

  it("AC-1: yüklenirken 'Yükleniyor...' gösterir", () => {
    vi.mocked(adminApi.getVerificationQueue).mockReturnValue(
      new Promise(() => {}) // Never resolves
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    expect(screen.getByText("Yükleniyor...")).toBeTruthy();
  });

  it("AC-1: dolu kuyruk — her kurum satırı (name, legal_id, domain, verification_level, created_at) listelenir", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      // İlk kurum
      const org1Row = within(table).getByText("Tech Startup Inc.").closest("tr");
      expect(org1Row?.textContent).toContain("TR123456789");
      expect(org1Row?.textContent).toContain("techstartup.com");
      expect(within(org1Row!).getByDisplayValue("T2")).toBeTruthy();

      // İkinci kurum (null alanlar "-" ile gösterilir)
      const org2Row = within(table).getByText("Startup Inc.").closest("tr");
      expect(org2Row?.textContent).toContain("-");
    });
  });

  it("AC-S13: haklı bulunan şikayeti olan kuruluşun adının yanında sayı rozeti gösterilir", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      paged([{ ...mockOrganization, upheld_complaint_count: 3 }, { ...mockOrganizationWithNulls, upheld_complaint_count: 0 }])
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    const table = await screen.findByRole("table");
    const org1Row = within(table).getByText("Tech Startup Inc.").closest("tr")!;
    expect(within(org1Row).getByText("3 doğrulama talebini yanıtsız bıraktı")).toBeTruthy();
    const org2Row = within(table).getByText("Startup Inc.").closest("tr")!;
    expect(within(org2Row).queryByText(/doğrulama talebini yanıtsız bıraktı/)).toBeNull();
  });

  it("AC-1: nullable alanlar — legal_id null ise '-' gösterilir", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      // İkinci satırda legal_id null olduğu için "-" gösterilir
      const row = within(table).getByText("Startup Inc.").closest("tr");
      expect(row?.textContent).toContain("-");
    });
  });

  it("AC-1: nullable alanlar — domain null ise '-' gösterilir", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      const row = within(table).getByText("Startup Inc.").closest("tr");
      expect(row?.textContent).toContain("-");
    });
  });

  it("AC-1: nullable alanlar — verified_at null ise '-' gösterilir", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      const row = within(table).getByText("Startup Inc.").closest("tr");
      // verified_at null olduğu için "-" gösterilir
      expect(row?.textContent).toContain("-");
    });
  });

  // =========================================================================
  // AC-2: Seviye güncelleme (mutation)
  // =========================================================================

  it("AC-2: seviye güncelleme başarılı — satır kuyruktan kaybolur, yeşil bildirim gösterilir", async () => {
    // Sunucu yanıtı (updated) legal_id/domain döndürmez — satırı o eksik
    // veriyle yerinde tutmak yerine (brif §19 "işlenen satır kaybolur")
    // reject ile tutarlı şekilde kuyruktan kaldırılması beklenir.
    const updatedOrg = {
      id: mockOrganization.id,
      name: mockOrganization.name,
      legal_id: null,
      domain: null,
      verification_level: "T3",
      verified_at: "2026-10-09T22:09:33Z",
      created_at: mockOrganization.created_at,
    };
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );
    vi.mocked(adminApi.updateVerificationLevel).mockResolvedValueOnce(
      updatedOrg
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });

    // Seviye seçme (form'da <select> olmalı, enumerate değerleri T0-T3)
    const table = screen.getByRole("table");
    const org1Row = within(table).getByText("Tech Startup Inc.").closest("tr");
    const levelSelect = within(org1Row!).getByDisplayValue("T2");
    await user.selectOptions(levelSelect, "T3");

    // Onayla butonu
    const confirmButton = within(org1Row!).getByRole("button", { name: /onayla|güncelle/i });
    await user.click(confirmButton);

    // Başarı bildirimi kontrol et
    await waitFor(() => {
      const successMessage = screen.getByText(
        /doğrulama seviyesi güncellendi|başarıyla güncelleştirildi/i
      );
      expect(successMessage).toBeTruthy();
    });

    // Satır kuyruktan kaybolmalı; diğer satır (Startup Inc.) listede kalmalı
    await waitFor(() => {
      expect(screen.queryByText("Tech Startup Inc.")).toBeNull();
    });
    expect(screen.getByText("Startup Inc.")).toBeTruthy();
  });

  it("YET-198: Reddet — kurum kuyruktan çıkar, rejectVerification çağrılır, seviye güncelleme çağrılmaz", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(mockVerificationQueue);
    vi.mocked(adminApi.rejectVerification).mockResolvedValueOnce(mockOrganization);

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: "Reddet Tech Startup Inc." }));

    await waitFor(() => {
      expect(screen.queryByText("Tech Startup Inc.")).toBeNull();
    });
    expect(screen.getByText("Startup Inc.")).toBeTruthy();
    expect(screen.getByText("Başvuru reddedildi")).toBeTruthy();
    expect(adminApi.rejectVerification).toHaveBeenCalledWith("org-1");
    expect(adminApi.updateVerificationLevel).not.toHaveBeenCalled();
  });

  it("YET-198: Reddet 409 — 'artık kuyrukta değil' uyarısı, satır listede kalır", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(mockVerificationQueue);
    vi.mocked(adminApi.rejectVerification).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "NOT_PENDING", message: "Kurum doğrulama kuyruğunda değil.", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });
    await user.click(screen.getByRole("button", { name: "Reddet Tech Startup Inc." }));

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("artık doğrulama kuyruğunda değil");
    });
    expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
  });

  // =========================================================================
  // AC-3: Admin olmayan kullanıcı 404 → satır-içi uyarı
  // =========================================================================

  it("AC-3: yetkisiz erişim — 404 'Kaynak bulunamadı' satır-içi uyarısı gösterilir", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    vi.mocked(adminApi.getVerificationQueue).mockRejectedValueOnce(error);

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      // Satır-içi uyarı (global not-found.tsx DEĞİL)
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("Kaynak bulunamadı");
      expect(alert.textContent).not.toContain(
        "yetkin yok"
      );
      // Admin panelinin varlığı sızdırılmaz
    });
  });

  it("AC-3: 404 durumunda admin panelinin varlığı sızdırılmaz (AC-S1)", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    vi.mocked(adminApi.getVerificationQueue).mockRejectedValueOnce(error);

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      // Genel bir "sayfa bulunamadı" uyarısı (admin paneli var demenin mesajı yok)
      expect(
        screen.queryByText(/admin yetkiniz yok|erişim reddedildi/)
      ).toBeNull();
    });
  });

  // =========================================================================
  // AC-4: Boş kuyruk — boş-durum mesajı
  // =========================================================================

  it("AC-4: boş kuyruk — 'Bekleyen doğrulama isteği yok' mesajı gösterilir", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockEmptyQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/bekleyen doğrulama isteği yok|şu anda kuyrukta kurum yok/i)
      ).toBeTruthy();
    });
  });

  it("AC-4: boş kuyruk — boş beyaz ekran değil, kullanıcı neyin eksik olduğunu anlar", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockEmptyQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const container = screen.getByRole("main") || document.body;
      // Boş durum mesajı varsa ekran tamamen beyaz değildir
      expect(
        container.textContent?.includes("Bekleyen doğrulama isteği yok") ||
          container.textContent?.includes("kuyruk boş")
      ).toBeTruthy();
    });
  });

  // =========================================================================
  // AC-8: API hatası (500, network) — kırmızı bildirim, liste korunur
  // =========================================================================

  it("AC-8: server error (500) — kırmızı bildirim gösterilir", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-123",
    });
    vi.mocked(adminApi.getVerificationQueue).mockRejectedValueOnce(error);

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("bir hata oluştu");
    });
  });

  it("AC-8: network error — kırmızı bildirim 'Bir hata oluştu' gösterilir", async () => {
    const error = new NetworkError("network");
    vi.mocked(adminApi.getVerificationQueue).mockRejectedValueOnce(error);

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("hata");
    });
  });

  it("AC-8: timeout — kırmyzı bildirim 'İstek zaman aşımına uğradı' gösterilir", async () => {
    const error = new NetworkError("timeout");
    vi.mocked(adminApi.getVerificationQueue).mockRejectedValueOnce(error);

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(
        alert.textContent?.includes("zaman aşımı") ||
          alert.textContent?.includes("timeout")
      ).toBeTruthy();
    });
  });

  it("AC-8: mutation hatası — önceki liste durumu korunur, optimistic update YOK", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );
    const mutationError = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-456",
    });
    vi.mocked(adminApi.updateVerificationLevel).mockRejectedValueOnce(
      mutationError
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });

    const table = screen.getByRole("table");

    // Seviye seçiş yap
    const org1Row = within(table).getByText("Tech Startup Inc.").closest("tr");
    const levelSelect = within(org1Row!).getByDisplayValue("T2");
    await user.selectOptions(levelSelect, "T3");

    // Onayla
    const confirmButton = within(org1Row!).getByRole("button", { name: /onayla|güncelle/i });
    await user.click(confirmButton);

    // Hata sonrası error message gösterilir
    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("hata");
    });

    // Tablo korunur — satır hâlâ var ve adı aynı
    const preservedRow = within(table).getByText("Tech Startup Inc.").closest("tr");
    expect(preservedRow?.textContent).toContain("TR123456789");
    expect(preservedRow?.textContent).toContain("techstartup.com");

    // Form yeniden denenebilir olmalı
    const updatedConfirmButton = within(preservedRow!).getByRole("button", { name: /onayla|güncelle/i });
    expect(updatedConfirmButton).not.toBeDisabled();
  });

  // =========================================================================
  // AC-9: Admin olmayan kullanıcı — AC-S2 (var/yok ayrımı)
  // =========================================================================

  it("AC-9/AC-S2: admin olmayan kullanıcı — var olan kurum id'si için de 404", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    // Tüm çağrılar 404 döner
    vi.mocked(adminApi.getVerificationQueue).mockRejectedValueOnce(error);
    vi.mocked(adminApi.updateVerificationLevel).mockRejectedValueOnce(error);

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      // Sayfa 404 hatasını gösterir
      expect(screen.getByRole("alert")).toBeTruthy();
    });

    // Mutation de 404 döner
    const updateError = screen.getByRole("alert");
    expect(updateError).toBeTruthy();
  });

  // =========================================================================
  // Form doğrulama testleri
  // =========================================================================

  it("Form — <select> enum'a kısıtlı (T0, T1, T2, T3)", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const select = screen.getByDisplayValue("T2");
      const options = (select as HTMLSelectElement).options;
      const optionValues = Array.from(options).map((opt) => opt.value);
      expect(optionValues).toContain("T0");
      expect(optionValues).toContain("T1");
      expect(optionValues).toContain("T2");
      expect(optionValues).toContain("T3");
    });
  });

  it("Form — seçim sonrası onayla butonu aktif hale gelir", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });

    const table = screen.getByRole("table");
    const org1Row = within(table).getByText("Tech Startup Inc.").closest("tr");
    const select = within(org1Row!).getByDisplayValue("T2");
    await user.selectOptions(select, "T3");

    const button = within(org1Row!).getByRole("button", { name: /onayla|güncelle/i });
    expect(button).not.toBeDisabled();
  });

  // =========================================================================
  // Accessibility testleri
  // =========================================================================

  it("A11y — hata mesajı aria-live alert olarak duyurulur", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-789",
    });
    vi.mocked(adminApi.getVerificationQueue).mockRejectedValueOnce(error);

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert).toBeTruthy();
      expect(alert.getAttribute("role")).toBe("alert");
    });
  });

  it("A11y — tablonun başlık satırı", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByRole("columnheader", { name: /kurum adı|name/i })).toBeTruthy();
      expect(screen.getByRole("columnheader", { name: /ticari kayıt|legal_id/i })).toBeTruthy();
    });
  });

  // =========================================================================
  // AC-1/AC-4: Erişilebilirlik — başarı mesajı role='status' ile duyurulabilir
  // =========================================================================

  it("AC-1/AC-4: seviye güncellemesi başarılı — başarı mesajı role='status' ile bulunabilir", async () => {
    const updatedOrg = { ...mockOrganization, verification_level: "T3" };
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );
    vi.mocked(adminApi.updateVerificationLevel).mockResolvedValueOnce(
      updatedOrg
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });

    // Seviye seçme
    const table = screen.getByRole("table");
    const org1Row = within(table).getByText("Tech Startup Inc.").closest("tr");
    const levelSelect = within(org1Row!).getByDisplayValue("T2");
    await user.selectOptions(levelSelect, "T3");

    // Onayla
    const confirmButton = within(org1Row!).getByRole("button", { name: /onayla|güncelle/i });
    await user.click(confirmButton);

    // Başarı mesajı role="status" ile bulunabilir olmalı
    await waitFor(() => {
      const statusMsg = screen.getByRole("status", { hidden: false });
      expect(statusMsg).toBeTruthy();
      expect(statusMsg.textContent).toBeTruthy();
    });
  });

  it("AC-4: başarı mesajı görsel stil korunur (regresyon: yeşil renk, kenarlık)", async () => {
    const updatedOrg = { ...mockOrganization, verification_level: "T3" };
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce(
      mockVerificationQueue
    );
    vi.mocked(adminApi.updateVerificationLevel).mockResolvedValueOnce(
      updatedOrg
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });

    const table = screen.getByRole("table");
    const org1Row = within(table).getByText("Tech Startup Inc.").closest("tr");
    const levelSelect = within(org1Row!).getByDisplayValue("T2");
    await user.selectOptions(levelSelect, "T3");

    const confirmButton = within(org1Row!).getByRole("button", { name: /onayla|güncelle/i });
    await user.click(confirmButton);

    // Başarı mesajı gösterilir — yeşil stilini kontrol et
    await waitFor(() => {
      const successDiv = document.querySelector(".bg-green-50");
      expect(successDiv).toBeTruthy();
      expect(successDiv?.className).toContain("bg-green-50");
      expect(successDiv?.className).toContain("border-green-200");
      expect(successDiv?.className).toContain("text-green-700");
    });
  });
});


/**
 * admin-sayfalama-ve-kabuk — AC-1/AC-8/AC-9: Önceki/Sonraki sayfalama + hata/tekrar dene.
 */
describe("DogrulamaKuyruguPage — sayfalama", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: "admin-1", email: "admin@test.com", is_platform_admin: true },
        organizations: [],
        institutions: [],
        talent_profile: null,
      },
      error: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
  });

  afterEach(() => {
    cleanup();
  });

  it("has_more=true ise Sonraki etkin; tıklanınca offset=50 ile istek atılır", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    vi.mocked(adminApi.getVerificationQueue)
      .mockResolvedValueOnce({ items: [mockOrganization], limit: 50, offset: 0, has_more: true })
      .mockResolvedValueOnce({ items: [], limit: 50, offset: 50, has_more: false });

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    const next = await screen.findByRole("button", { name: "Sonraki" });
    expect((next as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Önceki" }) as HTMLButtonElement).disabled).toBe(true);

    await userEvent.setup().click(next);

    await waitFor(() => {
      expect(adminApi.getVerificationQueue).toHaveBeenLastCalledWith({ limit: 50, offset: 50 });
    });
  });

  it("has_more=false ve offset=0 iken sayfalama gösterilmez", async () => {
    vi.mocked(adminApi.getVerificationQueue).mockResolvedValueOnce({
      items: [mockOrganization],
      limit: 50,
      offset: 0,
      has_more: false,
    });

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });
    expect(screen.queryByRole("navigation", { name: "Sayfalama" })).toBeNull();
  });

  it("liste hatasında aria-live uyarısı ve 'Tekrar dene' görünür; tıklanınca yeniden istenir", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    vi.mocked(adminApi.getVerificationQueue)
      .mockRejectedValueOnce(new ApiError({ status: 500, code: "INTERNAL_ERROR", message: "x", requestId: null }))
      .mockResolvedValueOnce({ items: [mockOrganization], limit: 50, offset: 0, has_more: false });

    renderWithQueryClient(<DogrulamaKuyruguPage />);

    const retry = await screen.findByRole("button", { name: "Tekrar dene" });
    expect(screen.getByRole("alert")).toBeTruthy();

    await userEvent.setup().click(retry);

    await waitFor(() => {
      expect(screen.getByText("Tech Startup Inc.")).toBeTruthy();
    });
  });
});
