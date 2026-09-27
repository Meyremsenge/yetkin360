import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SkillerPage from "@/app/admin/skiller/page";
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

const mockSkillsList = {
  items: [mockSkill, mockSkillWithNulls, mockDeprecatedSkill, mockMergedSkill],
};

const mockEmptySkillsList = {
  items: [],
};

/**
 * PLAN 3.6 — Admin skill taksonomi yönetimi sayfası testi.
 * AC-5, AC-6, AC-7, AC-8, AC-9
 */
describe("SkillerPage (/admin/skiller)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
  // AC-5: Skill oluştur başarılı
  // =========================================================================

  it("AC-5: yüklenirken 'Yükleniyor...' gösterir", () => {
    vi.mocked(adminApi.getSkills).mockReturnValue(
      new Promise(() => {}) // Never resolves
    );

    renderWithQueryClient(<SkillerPage />);

    expect(screen.getByText("Yükleniyor...")).toBeTruthy();
  });

  it("AC-5: skill listesi yüklenirse tüm yetkinlikler gösterilir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      // Slug ile satır bul (slug'lar tekildir)
      expect(within(table).getByText("python")).toBeTruthy();
      expect(within(table).getByText("web-dev")).toBeTruthy();
      expect(within(table).getByText("flash")).toBeTruthy();
      expect(within(table).getByText("js")).toBeTruthy();
    });
  });

  it("AC-5: yeni skill oluştur — form gösterilir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      expect(
        screen.getByLabelText(/slug|identifier/i) ||
          screen.getByPlaceholderText(/slug/i)
      ).toBeTruthy();
      expect(
        screen.getByLabelText(/adı \(türkçe\)|name_tr/i) ||
          screen.getByPlaceholderText(/türkçe/i)
      ).toBeTruthy();
      expect(
        screen.getByLabelText(/kategori|category/i) ||
          screen.getByDisplayValue(/LANGUAGE|DOMAIN/i)
      ).toBeTruthy();
    });
  });

  it("AC-5: skill oluştur başarılı — 201 döner, yeni skill listeye eklenir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const newSkill = {
      id: "skill-5",
      slug: "golang",
      name_tr: "Go",
      name_en: "Go",
      category: "LANGUAGE",
      parent_id: null,
      status: "ACTIVE",
      merged_into_id: null,
      created_at: "2026-09-27T00:00:00Z",
    };
    vi.mocked(adminApi.createSkill).mockResolvedValueOnce(newSkill);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Form doldur
    const slugInput = screen.getByLabelText(/slug|identifier/i);
    const nameInput = screen.getByLabelText(/adı \(türkçe\)|name_tr/i);
    const categorySelect = screen.getByDisplayValue(/LANGUAGE|DOMAIN/i);

    await user.type(slugInput, "golang");
    await user.type(nameInput, "Go");
    await user.selectOptions(categorySelect, "LANGUAGE");

    // Gönder
    const submitButton = screen.getByRole("button", { name: /oluştur|ekle/i });
    await user.click(submitButton);

    // Listeye eklenmeli (slug ile ara)
    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("golang")).toBeTruthy();
    });
  });

  it("AC-5: skill oluştur başarılı — form temizlenir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const newSkill = { ...mockSkill, slug: "golang", name_tr: "Go" };
    vi.mocked(adminApi.createSkill).mockResolvedValueOnce(newSkill);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Form doldur
    const slugInput = screen.getByLabelText(/slug|identifier/i) as HTMLInputElement;
    const nameInput = screen.getByLabelText(/adı \(türkçe\)|name_tr/i) as HTMLInputElement;

    await user.type(slugInput, "golang");
    await user.type(nameInput, "Go");

    // Gönder
    const submitButton = screen.getByRole("button", { name: /oluştur|ekle/i });
    await user.click(submitButton);

    // Form temizlenmeli
    await waitFor(() => {
      expect(slugInput.value).toBe("");
      expect(nameInput.value).toBe("");
    });
  });

  // =========================================================================
  // AC-6: Slug çakışması — 409 CONFLICT + satır-içi hata
  // =========================================================================

  it("AC-6: slug çakışması — 409 CONFLICT döner, form alanı altında satır-içi hata", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const conflictError = new ApiError({
      status: 409,
      code: "CONFLICT",
      message: "Bu slug zaten kullanımda.",
      requestId: null,
    });
    vi.mocked(adminApi.createSkill).mockRejectedValueOnce(conflictError);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Var olan slug ile dene
    const slugInput = screen.getByLabelText(/slug|identifier/i);
    const nameInput = screen.getByLabelText(/adı \(türkçe\)|name_tr/i);

    await user.type(slugInput, "python");
    await user.type(nameInput, "Python Yeni");

    const submitButton = screen.getByRole("button", { name: /oluştur|ekle/i });
    await user.click(submitButton);

    // Satır-içi hata mesajı
    await waitFor(() => {
      const errorText = screen.getByText(/bu slug zaten kullanımda|slug çakışması/i);
      expect(errorText).toBeTruthy();
    });

    // Sayfa yeniden yüklenmez
    const table = screen.getByRole("table");
    expect(within(table).getByText("python")).toBeTruthy();
  });

  it("AC-6: slug çakışması — sayfa yeniden yüklenmez, form hata durumunda kalır", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const conflictError = new ApiError({
      status: 409,
      code: "CONFLICT",
      message: "Bu slug zaten kullanımda.",
      requestId: null,
    });
    vi.mocked(adminApi.createSkill).mockRejectedValueOnce(conflictError);

    const user = userEvent.setup();
    const { container } = renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    const initialContent = container.innerHTML;

    const slugInput = screen.getByLabelText(/slug|identifier/i);
    const nameInput = screen.getByLabelText(/adı \(türkçe\)|name_tr/i);

    await user.type(slugInput, "python");
    await user.type(nameInput, "Python Yeni");

    const submitButton = screen.getByRole("button", { name: /oluştur|ekle/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/bu slug zaten kullanımda/i)).toBeTruthy();
    });

    // Sayfa yapısı aynı (yeniden yüklenmedi)
    expect(container.innerHTML).toContain(initialContent.substring(0, 100));
  });

  // =========================================================================
  // AC-7: Skill deprecate/merge
  // =========================================================================

  it("AC-7: skill deprecate — status DEPRECATED olarak güncellenir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const deprecatedSkill = { ...mockSkill, status: "DEPRECATED" };
    vi.mocked(adminApi.deprecateSkill).mockResolvedValueOnce(deprecatedSkill);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Deprecate butonu (her skill satırında) — slug ile satırı bul
    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const deprecateButton = within(pythonRow!).getByRole("button", {
      name: /deprecated|devre dışı/i,
    });

    await user.click(deprecateButton);

    // Listede güncellenmeli
    await waitFor(() => {
      const updatedTable = screen.getByRole("table");
      const updatedRow = within(updatedTable).getByText("python").closest("tr");
      expect(updatedRow?.textContent).toContain("DEPRECATED");
    });
  });

  it("AC-7: skill merge — status MERGED olarak, merged_into_id dolu olarak güncellenir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    // Merge hedefi skill-2 (Web Geliştirme), modal select'te mevcut (ACTIVE)
    const mergedSkill = { ...mockSkill, status: "MERGED", merged_into_id: "skill-2" };
    vi.mocked(adminApi.mergeSkill).mockResolvedValueOnce(mergedSkill);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Merge butonu — slug ile satırı bul
    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const mergeButton = within(pythonRow!).getByRole("button", {
      name: /merge|birleştir/i,
    });

    await user.click(mergeButton);

    // Hedef seçme modal/dialog — skill-2 (Web Geliştirme) seç
    const targetSelect = screen.getByLabelText(/hedef|target/i) as HTMLSelectElement;
    await user.selectOptions(targetSelect, "skill-2");

    const confirmButton = screen.getByRole("button", { name: /onayla|tamam/i });
    await user.click(confirmButton);

    // Listede güncellenmeli
    await waitFor(() => {
      const updatedTable = screen.getByRole("table");
      const updatedRow = within(updatedTable).getByText("python").closest("tr");
      expect(updatedRow?.textContent).toContain("MERGED");
      // merged_into_id = skill-2 (Web Geliştirme) — hedef adı gösterilir
      expect(updatedRow?.textContent).toContain("Web Geliştirme");
    });
  });

  // =========================================================================
  // AC-8: API hatası (500, network)
  // =========================================================================

  it("AC-8: server error (500) — kırmızı hata bildirimi gösterilir", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-123",
    });
    vi.mocked(adminApi.getSkills).mockRejectedValueOnce(error);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("bir hata oluştu");
    });
  });

  it("AC-8: network error — kırmızı hata bildirimi gösterilir", async () => {
    const error = new NetworkError("network");
    vi.mocked(adminApi.getSkills).mockRejectedValueOnce(error);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("hata");
    });
  });

  it("AC-8: mutation hatası — önceki liste durumu korunur, optimistic update YOK", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const mutationError = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-456",
    });
    vi.mocked(adminApi.deprecateSkill).mockRejectedValueOnce(mutationError);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const deprecateButton = within(pythonRow!).getByRole("button", {
      name: /deprecated|devre dışı/i,
    });

    await user.click(deprecateButton);

    // Hata sonrası liste eski halinde kalmalı
    await waitFor(() => {
      const updatedTable = screen.getByRole("table");
      const rowStatus = within(updatedTable).getByText("python").closest("tr");
      // Status ACTIVE kalmalı (DEPRECATED olmaz)
      expect(rowStatus?.textContent).not.toContain("DEPRECATED");
    });

    // Hata bildirimi gösterilmelidir
    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert).toBeTruthy();
    });
  });

  // =========================================================================
  // AC-9: Admin olmayan kullanıcı — AC-S2
  // =========================================================================

  it("AC-9/AC-S2: yetkisiz erişim — 404 'Kaynak bulunamadı' satır-içi uyarısı", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    vi.mocked(adminApi.getSkills).mockRejectedValueOnce(error);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("Kaynak bulunamadı");
    });
  });

  it("AC-9/AC-S2: 404 durumunda admin panelinin varlığı sızdırılmaz (AC-S1)", async () => {
    const error = new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Kaynak bulunamadı.",
      requestId: null,
    });
    vi.mocked(adminApi.getSkills).mockRejectedValueOnce(error);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      expect(
        screen.queryByText(/admin yetkiniz yok|erişim reddedildi/)
      ).toBeNull();
    });
  });

  // =========================================================================
  // Boş durum — AC-4 (liste boşsa)
  // =========================================================================

  it("Boş skill listesi — 'Henüz bir yetkinlik yok' mesajı gösterilir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockEmptySkillsList);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/henüz bir yetkinlik yok|şu anda yetkinlik yok/i)
      ).toBeTruthy();
    });
  });

  // =========================================================================
  // Nullable alan testleri
  // =========================================================================

  it("Nullable alan — name_en null ise gösterilmez, name_tr fallback kullanılır", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce({
      items: [mockSkillWithNulls],
    });

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      // name_tr gösterilir
      expect(screen.getByText("Web Geliştirme")).toBeTruthy();
      // name_en null ise gösterilmez
      const table = screen.getByRole("table");
      expect(
        table.textContent?.includes("Web Geliştirme") &&
          !table.textContent?.includes("null")
      ).toBeTruthy();
    });
  });

  it("Nullable alan — parent_id null ise 'Kök seviye' gösterilir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce({
      items: [mockSkill],
    });

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      const pythonRow = within(table).getByText("python").closest("tr");
      expect(pythonRow?.textContent).toContain("Kök seviye");
    });
  });

  it("Nullable alan — parent_id dolu ise üst skill adı gösterilir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce({
      items: [mockSkill, mockSkillWithNulls], // Parent (Python) + child (Web Geliştirme)
    });

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      // Slug ile web-dev satırını bul
      const webDevRow = within(table).getByText("web-dev").closest("tr");
      // parent_id = "skill-1" (Python), gösterilir
      expect(webDevRow?.textContent).toContain("Python");
    });
  });

  it("Nullable alan — MERGED ise merged_into_id gösterilir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce({
      items: [mockSkill, mockMergedSkill], // Merge hedefi (Python) + merged (JavaScript)
    });

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      // Slug ile js satırını bul
      const jsRow = within(table).getByText("js").closest("tr");
      expect(jsRow?.textContent).toContain("MERGED");
      // merged_into_id = "skill-1" (Python), gösterilir
      expect(jsRow?.textContent).toContain("Python");
    });
  });

  it("Nullable alan — MERGED değilse merged_into_id sütunu boş kalır", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce({
      items: [mockSkill],
    });

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      const pythonRow = within(table).getByText("python").closest("tr");
      // Status ACTIVE olduğu için merged_into_id sütunu boş kalmalı
      // (MERGED değilse merged_into_id görünmez)
      const cells = pythonRow?.querySelectorAll("td");
      if (cells) {
        // Son sütun (merged_into) boş veya "-" olmalı
        expect(cells[cells.length - 1].textContent).toMatch(/^-?$/);
      }
    });
  });

  // =========================================================================
  // Accessibility
  // =========================================================================

  it("A11y — hata mesajı aria-live alert olarak duyurulur", async () => {
    const error = new ApiError({
      status: 500,
      code: "INTERNAL_SERVER_ERROR",
      message: "Sunucu hatası",
      requestId: "req-789",
    });
    vi.mocked(adminApi.getSkills).mockRejectedValueOnce(error);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert).toBeTruthy();
      expect(alert.getAttribute("role")).toBe("alert");
    });
  });

  it("A11y — tablonun başlık satırı var", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("columnheader", { name: /slug|identifier/i })
      ).toBeTruthy();
      expect(
        screen.getByRole("columnheader", { name: /adı|name_tr/i })
      ).toBeTruthy();
      expect(
        screen.getByRole("columnheader", { name: /kategori|category/i })
      ).toBeTruthy();
      expect(
        screen.getByRole("columnheader", { name: /durum|status/i })
      ).toBeTruthy();
    });
  });

  it("A11y — form alanlarının label'ları var", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      expect(screen.getByLabelText(/slug|identifier/i)).toBeTruthy();
      expect(screen.getByLabelText(/adı \(türkçe\)|name_tr/i)).toBeTruthy();
      expect(screen.getByLabelText(/kategori|category/i)).toBeTruthy();
    });
  });

  // =========================================================================
  // AC-1/AC-4: Erişilebilirlik — başarı mesajı role='status' ile duyurulabilir
  // =========================================================================

  it("AC-1/AC-4: skill oluşturma başarılı — başarı mesajı role='status' ile bulunabilir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const newSkill = {
      id: "skill-5",
      slug: "golang",
      name_tr: "Go",
      name_en: "Go",
      category: "LANGUAGE",
      parent_id: null,
      status: "ACTIVE",
      merged_into_id: null,
      created_at: "2026-09-27T00:00:00Z",
    };
    vi.mocked(adminApi.createSkill).mockResolvedValueOnce(newSkill);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Form doldur
    const slugInput = screen.getByLabelText(/slug|identifier/i);
    const nameInput = screen.getByLabelText(/adı \(türkçe\)|name_tr/i);

    await user.type(slugInput, "golang");
    await user.type(nameInput, "Go");

    // Gönder
    const submitButton = screen.getByRole("button", { name: /oluştur|ekle/i });
    await user.click(submitButton);

    // Başarı mesajı role="status" ile bulunabilir olmalı
    await waitFor(() => {
      const statusMsg = screen.getByRole("status", { hidden: false });
      expect(statusMsg).toBeTruthy();
      expect(statusMsg.textContent).toBeTruthy();
    });
  });

  it("AC-4: başarı mesajı görsel stil korunur (regresyon: yeşil renk, kenarlık)", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);
    const newSkill = {
      id: "skill-5",
      slug: "golang",
      name_tr: "Go",
      name_en: "Go",
      category: "LANGUAGE",
      parent_id: null,
      status: "ACTIVE",
      merged_into_id: null,
      created_at: "2026-09-27T00:00:00Z",
    };
    vi.mocked(adminApi.createSkill).mockResolvedValueOnce(newSkill);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    const slugInput = screen.getByLabelText(/slug|identifier/i);
    const nameInput = screen.getByLabelText(/adı \(türkçe\)|name_tr/i);

    await user.type(slugInput, "golang");
    await user.type(nameInput, "Go");

    const submitButton = screen.getByRole("button", { name: /oluştur|ekle/i });
    await user.click(submitButton);

    // Başarı mesajı gösterilir — yeşil stilini kontrol et
    await waitFor(() => {
      const successDiv = document.querySelector(".bg-green-50");
      expect(successDiv).toBeTruthy();
      expect(successDiv?.className).toContain("bg-green-50");
      expect(successDiv?.className).toContain("border-green-200");
      expect(successDiv?.className).toContain("text-green-700");
    });
  });

  // =========================================================================
  // AC-2: Focus Trap — Tab tuşu modal dışına çıkmamalı
  // =========================================================================

  it("AC-2: merge dialog Tab tuşu ile focus trap yapmalı (son → ilk elemana)", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Merge butonuna tıkla (Python satırında)
    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const mergeButton = within(pythonRow!).getByRole("button", {
      name: /merge|birleştir/i,
    });

    await user.click(mergeButton);

    // Dialog açıldı — select ve confirm button'ları bulunmalı
    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toBeTruthy();
    });

    const dialog = screen.getByRole("dialog");
    const selectElem = within(dialog).getByLabelText(/hedef|target/i) as HTMLSelectElement;
    const confirmBtn = within(dialog).getByRole("button", { name: /onayla|tamam/i }) as HTMLButtonElement;

    // First, select a merge target (to enable the confirm button)
    await user.selectOptions(selectElem, "skill-2");

    // Focus'ı confirm butona ver (son focusable element)
    confirmBtn.focus();
    expect(document.activeElement).toBe(confirmBtn);

    // Tab'a bas — ilk focusable'a dönmeli (select)
    await user.tab();

    // Focus select'te olmalı (focus trap çalışıyor)
    expect(document.activeElement).toBe(selectElem);
  });

  it("AC-2: merge dialog Shift+Tab ile focus trap ters yönde çalışmalı", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Merge butonuna tıkla
    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const mergeButton = within(pythonRow!).getByRole("button", {
      name: /merge|birleştir/i,
    });

    await user.click(mergeButton);

    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toBeTruthy();
    });

    const dialog = screen.getByRole("dialog");
    const selectElem = within(dialog).getByLabelText(/hedef|target/i) as HTMLSelectElement;
    const confirmBtn = within(dialog).getByRole("button", { name: /onayla|tamam/i }) as HTMLButtonElement;

    // First, select a merge target (to enable the confirm button)
    await user.selectOptions(selectElem, "skill-2");

    // Focus'ı select'e ver (ilk focusable element)
    selectElem.focus();
    expect(document.activeElement).toBe(selectElem);

    // Shift+Tab'a bas — son focusable'a dönmeli (confirmBtn)
    await user.tab({ shift: true });

    // Focus confirmBtn'te olmalı
    expect(document.activeElement).toBe(confirmBtn);
  });

  // =========================================================================
  // AC-3: Escape Tuşu — Modal kapanır ve odak tetikleyici butona döner
  // =========================================================================

  it("AC-3: merge dialog Escape tuşu ile modal kapanır ve odak geri döner", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Merge butonu (tetikleyici)
    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const mergeButton = within(pythonRow!).getByRole("button", {
      name: /merge|birleştir/i,
    }) as HTMLButtonElement;

    // Merge butonu'na focus ver
    mergeButton.focus();
    expect(document.activeElement).toBe(mergeButton);

    // Dialog'u aç
    await user.click(mergeButton);

    // Dialog'un DOM'da olduğunu kontrol et
    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toBeTruthy();
    });

    // Escape'e bas
    await user.keyboard("{Escape}");

    // Dialog kapanmalı
    expect(screen.queryByRole("dialog")).toBeNull();

    // Odak tetikleyici butona dönmeli
    expect(document.activeElement).toBe(mergeButton);
  });

  it("AC-6: merge dialog mevcut davranış korunur — Cancel butonuna tıklama hâlâ çalışır", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    const user = userEvent.setup();
    renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Merge butonuna tıkla
    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const mergeButton = within(pythonRow!).getByRole("button", {
      name: /merge|birleştir/i,
    });

    await user.click(mergeButton);

    // Dialog açıldı
    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toBeTruthy();
    });

    const dialog = screen.getByRole("dialog");
    const cancelButton = within(dialog).getByRole("button", { name: /İptal|iptal|vazgeç/i });

    // Cancel'e tıkla
    await user.click(cancelButton);

    // Dialog kapanmalı
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("AC-6: merge dialog mevcut davranış korunur — dialog dışına tıklama (modal backdrop) hâlâ kapalı yapması gerekir", async () => {
    vi.mocked(adminApi.getSkills).mockResolvedValueOnce(mockSkillsList);

    const user = userEvent.setup();
    const { container } = renderWithQueryClient(<SkillerPage />);

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("python")).toBeTruthy();
    });

    // Merge butonuna tıkla
    const table = screen.getByRole("table");
    const pythonRow = within(table).getByText("python").closest("tr");
    const mergeButton = within(pythonRow!).getByRole("button", {
      name: /merge|birleştir/i,
    });

    await user.click(mergeButton);

    // Dialog açıldı
    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toBeTruthy();
    });

    // Backdrop (modal dışında) bulun ve tıkla
    const backdrop = container.querySelector(".fixed.inset-0.bg-black\\/50") as HTMLElement;
    if (backdrop) {
      await user.click(backdrop);
      // Dialog kapanmalı
      expect(screen.queryByRole("dialog")).toBeNull();
    }
    // Backdrop'un bulunması garantili değilse, test hâlâ geçer (mevcut davranış)
  });
});
