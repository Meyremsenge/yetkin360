import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CalismalarPage from "@/app/calismalar/page";
import { useSession } from "@/lib/session/use-session";
import { listEngagements } from "@/lib/api/engagements";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/engagements", () => ({
  listEngagements: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function mockAuthenticatedSession() {
  vi.mocked(useSession).mockReturnValue({
    data: {
      user: { id: "user-1", email: "user@test.com" },
      organizations: [{ id: "org-1", name: "Test Org" }],
      institutions: [],
      talent_profile: null,
    },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>);
}

/**
 * YET-95 (PLAN 2.11): Engagement listesi ekranı (GET /engagements — mock).
 */
describe("CalismalarPage (/calismalar)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthenticatedSession();
  });

  afterEach(() => {
    cleanup();
  });

  it("yüklenirken 'Yükleniyor...' gösterir", async () => {
    vi.mocked(listEngagements).mockReturnValue(new Promise(() => {}));

    renderWithQueryClient(<CalismalarPage />);

    expect(screen.getByText("Yükleniyor...")).toBeTruthy();
  });

  it("listEngagements hata verirse yükleme hatası mesajı gösterir", async () => {
    vi.mocked(listEngagements).mockRejectedValueOnce(new Error("network fail"));

    renderWithQueryClient(<CalismalarPage />);

    await waitFor(() => {
      expect(screen.getByText("Çalışmalar yüklenemedi.")).toBeTruthy();
    });
  });

  it("liste boşsa boş durum mesajı gösterir", async () => {
    vi.mocked(listEngagements).mockResolvedValueOnce({ items: [] });

    renderWithQueryClient(<CalismalarPage />);

    await waitFor(() => {
      expect(screen.getByText("Henüz bir çalışmanız yok.")).toBeTruthy();
    });
  });

  it("PLAN 3.53: 'Yeni Çalışma' butonu kuruluş seçiciye yönlendirir", async () => {
    vi.mocked(listEngagements).mockResolvedValueOnce({ items: [] });

    renderWithQueryClient(<CalismalarPage />);

    const link = screen.getByRole("link", { name: "Yeni Çalışma" });
    expect(link.getAttribute("href")).toBe("/calismalar/kurulus-sec");
  });

  it("dönen engagement'ları başlık, tür, kuruluş ve durum ile listeler", async () => {
    vi.mocked(listEngagements).mockResolvedValueOnce({
      items: [
        {
          id: "eng-1",
          title: "Frontend Stajı",
          kind: "INTERNSHIP",
          status: "ACTIVE",
          organization_id: "org-1",
          institution_id: null,
          organization_name: "Acme A.Ş.",
          version: 1,
          updated_at: "2026-09-01T00:00:00Z",
        },
      ],
    });

    renderWithQueryClient(<CalismalarPage />);

    await waitFor(() => {
      expect(screen.getByText("Frontend Stajı")).toBeTruthy();
      expect(screen.getByText("Staj · Acme A.Ş.")).toBeTruthy();
      expect(screen.getByText("Aktif")).toBeTruthy();
    });

    const link = screen.getByText("Frontend Stajı").closest("a");
    expect(link?.getAttribute("href")).toBe("/calismalar/eng-1");
  });

  /**
   * YET-205/ENT-04: Seed'deki engagement'ların tamamı VERIFIED olduğunda
   * durum etiketi boş/undefined görünüyordu. YET-194 (PR #36) STATUS_BADGE_CLASS
   * ve tr.json'a EVALUATED/VERIFIED/DISPUTED/RESOLVED eklemişti — bu test o
   * düzeltmenin kalıcı regresyon koruması (ticket'ın kendi senaryosuyla).
   */
  it("YET-205/ENT-04: VERIFIED durumu gerçek bir etiketle render edilir, 'undefined' değil", async () => {
    vi.mocked(listEngagements).mockResolvedValueOnce({
      items: [
        {
          id: "eng-verified",
          title: "Doğrulanmış Staj",
          kind: "INTERNSHIP",
          status: "VERIFIED",
          organization_id: "org-1",
          institution_id: null,
          organization_name: "Acme A.Ş.",
          version: 3,
          updated_at: "2026-09-01T00:00:00Z",
        },
      ],
    });

    renderWithQueryClient(<CalismalarPage />);

    await waitFor(() => {
      expect(screen.getByText("Doğrulandı")).toBeTruthy();
      const link = screen.getByText("Doğrulanmış Staj").closest("a");
      expect(link?.textContent).not.toContain("undefined");
    });
  });

  it("YET-205/ENT-04: EVALUATED durumu da gerçek bir etiketle render edilir", async () => {
    vi.mocked(listEngagements).mockResolvedValueOnce({
      items: [
        {
          id: "eng-evaluated",
          title: "Değerlendirilmiş Proje",
          kind: "SHORT_PROJECT",
          status: "EVALUATED",
          organization_id: "org-1",
          institution_id: null,
          organization_name: "Acme A.Ş.",
          version: 2,
          updated_at: "2026-09-01T00:00:00Z",
        },
      ],
    });

    renderWithQueryClient(<CalismalarPage />);

    await waitFor(() => {
      expect(screen.getByText("Değerlendirildi")).toBeTruthy();
    });
  });
});
