import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PublicVerificationPage from "@/app/v/[token]/page";
import { useParams } from "next/navigation";
import { getPublicVerification } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));
vi.mock("@/lib/api/public", () => ({
  getPublicVerification: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockPublicVerification = {
  title: "Yazılım Stajyeri",
  talent_name: "Ayşe Yılmaz",
  organization_name: "Acme A.Ş.",
  organization_trust_level: "T2",
  institution_name: "ODTÜ",
  started_on: "2025-01-01",
  ended_on: "2025-06-30",
  verified_at: "2026-09-20T10:00:00Z",
  attested_skills: [
    {
      name_tr: "Python",
      claim_type: "COMPETENCE",
      attestor_organization: "Acme A.Ş.",
    },
  ],
};

/**
 * YET-112 (PLAN 3.8): Public doğrulama sayfası — anonim ziyaretçi tarafından doğrulama linki görüntülenmesi.
 * AC-2, AC-4, AC-8, AC-9 test edilir.
 */
describe("PublicVerificationPage (/v/[token])", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ token: "test-verification-token" });
  });

  afterEach(() => {
    cleanup();
  });

  // AC-2: Happy path — verification detayları render edilir
  it("AC-2: Geçerli token → doğrulama detaylarını render eder (title, talent_name, organization, institution, skills)", async () => {
    vi.mocked(getPublicVerification).mockResolvedValueOnce(mockPublicVerification);

    renderWithQueryClient(<PublicVerificationPage />);

    await waitFor(() => {
      expect(screen.getByText("Yazılım Stajyeri")).toBeTruthy();
      expect(screen.getByText("Ayşe Yılmaz")).toBeTruthy();
      expect(screen.getByText("Acme A.Ş.")).toBeTruthy();
      expect(screen.getByText("ODTÜ")).toBeTruthy();
      expect(screen.getByText("Python")).toBeTruthy();
      expect(screen.getByText("T2")).toBeTruthy();
    });
  });

  // AC-4: 404 ApiError — "Kayıt bulunamadı"
  it("AC-4: Geçersiz token → 404 'Kayıt bulunamadı' gösterir", async () => {
    vi.mocked(getPublicVerification).mockRejectedValueOnce(
      new ApiError({
        status: 404,
        code: "VERIFICATION_NOT_FOUND",
        message: "Kayıt bulunamadı",
        requestId: null,
      })
    );

    renderWithQueryClient(<PublicVerificationPage />);

    await waitFor(() => {
      expect(screen.getByText("Kayıt bulunamadı")).toBeTruthy();
    });
  });

  // AC-8: NetworkError — genel hata mesajı (404'ten AYRI)
  it("AC-8: API timeout hatası → genel hata mesajı (404'ten AYRI)", async () => {
    vi.mocked(getPublicVerification).mockRejectedValueOnce(new NetworkError("timeout"));

    renderWithQueryClient(<PublicVerificationPage />);

    await waitFor(() => {
      // 404 mesajı olmamalı
      expect(screen.queryByText("Kayıt bulunamadı")).toBeNull();
      // NetworkError timeout mesajı: "İstek zaman aşımına uğradı"
      expect(screen.getByText("İstek zaman aşımına uğradı")).toBeTruthy();
    });
  });

  // AC-9: Düz metin render kontrolü (dangerouslySetInnerHTML yok)
  it("AC-9: talent_name, organization_name, institution_name düz metin render edilir, dangerouslySetInnerHTML kullanılmaz", async () => {
    vi.mocked(getPublicVerification).mockResolvedValueOnce(mockPublicVerification);

    const { container } = renderWithQueryClient(<PublicVerificationPage />);

    await waitFor(() => {
      const talentNameElement = screen.getByText("Ayşe Yılmaz");
      expect(talentNameElement.textContent).toBe("Ayşe Yılmaz");
      expect(talentNameElement.innerHTML).not.toContain("<script>");
    });

    const orgNameElement = screen.getByText("Acme A.Ş.");
    expect(orgNameElement.textContent).toBe("Acme A.Ş.");
    expect(orgNameElement.innerHTML).not.toContain("<script>");

    const institutionElement = screen.getByText("ODTÜ");
    expect(institutionElement.textContent).toBe("ODTÜ");
    expect(institutionElement.innerHTML).not.toContain("<script>");
  });
});
