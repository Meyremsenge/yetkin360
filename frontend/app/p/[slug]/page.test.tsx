import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PublicProfilePage from "@/app/p/[slug]/page";
import { useParams } from "next/navigation";
import { getPublicProfile } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));
vi.mock("@/lib/api/public", () => ({
  getPublicProfile: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockPublicProfile = {
  display_name: "Ayşe Yılmaz",
  verified_experiences: [
    {
      id: "exp-1",
      organization_name_snapshot: "Acme A.Ş.",
      role_snapshot: "Yazılım Stajyeri",
      started_on_snapshot: "2025-01-01",
      ended_on_snapshot: "2025-06-30",
      claim_type: "COMPETENCE",
      created_at: "2026-09-20T10:00:00Z",
    },
  ],
};

/**
 * YET-112 (PLAN 3.8): Public profil sayfası — anonim ziyaretçi tarafından doğrulanmış deneyim görüntülenmesi.
 * AC-1, AC-3, AC-5, AC-8, AC-9 test edilir.
 */
describe("PublicProfilePage (/p/[slug])", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ slug: "ayse-yilmaz" });
  });

  afterEach(() => {
    cleanup();
  });

  // AC-1: Happy path — display_name ve verified_experiences render edilir
  it("AC-1: Geçerli slug → display_name ve verified_experiences kartlarını render eder", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce(mockPublicProfile);

    renderWithQueryClient(<PublicProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Ayşe Yılmaz")).toBeTruthy();
      expect(screen.getByText("Acme A.Ş.")).toBeTruthy();
      expect(screen.getByText("Yazılım Stajyeri")).toBeTruthy();
    });
  });

  // AC-3: 404 ApiError — "Kayıt bulunamadı" gösterilir
  it("AC-3: Geçersiz slug → 404 'Kayıt bulunamadı' gösterir", async () => {
    vi.mocked(getPublicProfile).mockRejectedValueOnce(
      new ApiError({
        status: 404,
        code: "TALENT_NOT_FOUND",
        message: "Kayıt bulunamadı",
        requestId: null,
      })
    );

    renderWithQueryClient(<PublicProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Kayıt bulunamadı")).toBeTruthy();
    });
  });

  // AC-5: Boş verified_experiences listesi — display_name görünür + boş durum mesajı (404 DEĞİL)
  it("AC-5: Geçerli slug ama boş verified_experiences → display_name görünür + boş durum mesajı (404 DEĞİL)", async () => {
    const profileWithEmptyExperiences = {
      ...mockPublicProfile,
      verified_experiences: [],
    };
    vi.mocked(getPublicProfile).mockResolvedValueOnce(profileWithEmptyExperiences);

    renderWithQueryClient(<PublicProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Ayşe Yılmaz")).toBeTruthy();
      expect(screen.getByText("henüz doğrulanmış deneyim yok")).toBeTruthy();
      // 404 mesajı gösterilmemeli
      expect(screen.queryByText("Kayıt bulunamadı")).toBeNull();
    });
  });

  // AC-8: NetworkError — 404'ten farklı genel hata mesajı
  it("AC-8: API network hatası → genel hata mesajı (404'ten AYRI)", async () => {
    vi.mocked(getPublicProfile).mockRejectedValueOnce(new NetworkError("network"));

    renderWithQueryClient(<PublicProfilePage />);

    await waitFor(() => {
      // 404 mesajı olmamalı
      expect(screen.queryByText("Kayıt bulunamadı")).toBeNull();
      // NetworkError mesajı: "Ağ hatası oluştu"
      expect(screen.getByText("Ağ hatası oluştu")).toBeTruthy();
    });
  });

  // AC-9: Düz metin render kontrolü (dangerouslySetInnerHTML yok)
  it("AC-9: display_name düz metin render edilir, dangerouslySetInnerHTML kullanılmaz", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce(mockPublicProfile);

    const { container } = renderWithQueryClient(<PublicProfilePage />);

    await waitFor(() => {
      const displayNameElement = screen.getByText("Ayşe Yılmaz");
      // textContent kontrolü — düz metin
      expect(displayNameElement.textContent).toBe("Ayşe Yılmaz");
      // XSS koruması: innerHTML'de script yok
      expect(displayNameElement.innerHTML).not.toContain("<script>");
    });

    const orgNameElement = screen.getByText("Acme A.Ş.");
    expect(orgNameElement.textContent).toBe("Acme A.Ş.");
    expect(orgNameElement.innerHTML).not.toContain("<script>");
  });
});
