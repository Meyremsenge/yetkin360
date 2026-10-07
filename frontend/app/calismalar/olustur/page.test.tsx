import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import CalismaOlusturPage from "./page";
import { createEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
}));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/engagements", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/engagements")>();
  return { ...actual, createEngagement: vi.fn() };
});

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockPush = vi.fn();

function mockSearchParams(organizationId: string | null) {
  vi.mocked(useSearchParams).mockReturnValue({
    get: (key: string) => (key === "organization_id" ? organizationId : null),
  } as unknown as ReturnType<typeof useSearchParams>);
}

function mockSessionWithTalent(talentId: string | undefined, institutionId: string | null = null) {
  vi.mocked(useSession).mockReturnValue({
    data: {
      user: { id: "user-1", email: "talent@test.com" },
      organizations: [],
      institutions: [],
      talent_profile: talentId ? { id: talentId, institution_id: institutionId } : null,
    },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>);
}

describe("CalismaOlusturPage (/calismalar/olustur)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  });

  afterEach(() => {
    cleanup();
  });

  it("organization_id query param yoksa eksik link mesajı gösterilir, form render edilmez", () => {
    mockSearchParams(null);
    mockSessionWithTalent("talent-1");

    renderWithQueryClient(<CalismaOlusturPage />);

    expect(screen.getByText(/Bu link eksik veya geçersiz/)).toBeTruthy();
    expect(screen.queryByLabelText("Başlık")).toBeNull();
  });

  it("talent_profile yoksa (öğrenci değil) ilgili mesaj gösterilir", () => {
    mockSearchParams("org-1");
    mockSessionWithTalent(undefined);

    renderWithQueryClient(<CalismaOlusturPage />);

    expect(screen.getByText(/yalnızca öğrenci hesapları için/)).toBeTruthy();
    expect(screen.queryByLabelText("Başlık")).toBeNull();
  });

  it("organization_id ve talent_profile varsa form render edilir — tür + başlık", () => {
    mockSearchParams("org-1");
    mockSessionWithTalent("talent-1");

    renderWithQueryClient(<CalismaOlusturPage />);

    expect(screen.getByLabelText("Tür")).toBeTruthy();
    expect(screen.getByLabelText("Başlık")).toBeTruthy();
  });

  it("happy path: doldurulup gönderilince createEngagement talent_id/organization_id otomatik ile çağrılır, detay sayfasına yönlendirilir", async () => {
    mockSearchParams("org-1");
    mockSessionWithTalent("talent-1", "inst-1");
    vi.mocked(createEngagement).mockResolvedValueOnce({
      id: "eng-new-1", talent_id: "talent-1", organization_id: "org-1", institution_id: "inst-1",
      kind: "INTERNSHIP", title: "Yeni Staj", status: "DRAFT", version: 1, reason: null,
      created_at: "2026-10-05T00:00:00Z", updated_at: "2026-10-05T00:00:00Z",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<CalismaOlusturPage />);

    await user.type(screen.getByLabelText("Başlık"), "Yeni Staj");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(createEngagement).toHaveBeenCalledWith({
        talent_id: "talent-1",
        organization_id: "org-1",
        kind: "INTERNSHIP",
        title: "Yeni Staj",
        institution_id: "inst-1",
      });
      expect(mockPush).toHaveBeenCalledWith("/calismalar/eng-new-1");
    });
  });

  it("talent'ın institution_id'si yoksa institution_id gönderilmeden çağrılır", async () => {
    mockSearchParams("org-1");
    mockSessionWithTalent("talent-1", null);
    vi.mocked(createEngagement).mockResolvedValueOnce({
      id: "eng-new-2", talent_id: "talent-1", organization_id: "org-1", institution_id: null,
      kind: "INTERNSHIP", title: "x", status: "DRAFT", version: 1, reason: null,
      created_at: "2026-10-05T00:00:00Z", updated_at: "2026-10-05T00:00:00Z",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<CalismaOlusturPage />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(createEngagement).toHaveBeenCalledWith(
        expect.objectContaining({ institution_id: undefined })
      );
    });
  });

  it("tür seçilirse payload'a doğru kind dahil edilir", async () => {
    mockSearchParams("org-1");
    mockSessionWithTalent("talent-1");
    vi.mocked(createEngagement).mockResolvedValueOnce({
      id: "eng-new-3", talent_id: "talent-1", organization_id: "org-1", institution_id: null,
      kind: "PART_TIME", title: "x", status: "DRAFT", version: 1, reason: null,
      created_at: "2026-10-05T00:00:00Z", updated_at: "2026-10-05T00:00:00Z",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<CalismaOlusturPage />);

    await user.selectOptions(screen.getByLabelText("Tür"), "PART_TIME");
    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(createEngagement).toHaveBeenCalledWith(expect.objectContaining({ kind: "PART_TIME" }));
    });
  });

  it("404 ORGANIZATION_NOT_FOUND → geçersiz link hatası gösterilir", async () => {
    mockSearchParams("org-bad");
    mockSessionWithTalent("talent-1");
    vi.mocked(createEngagement).mockRejectedValueOnce(
      new ApiError({ status: 404, code: "ORGANIZATION_NOT_FOUND", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<CalismaOlusturPage />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(screen.getByText("Bu organizasyon bulunamadı. Organizasyonunuzdan doğru linki isteyin.")).toBeTruthy();
    });
  });

  it("diğer hatalarda jenerik mesaj gösterilir", async () => {
    mockSearchParams("org-1");
    mockSessionWithTalent("talent-1");
    vi.mocked(createEngagement).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<CalismaOlusturPage />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(screen.getByText("İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin.")).toBeTruthy();
    });
  });
});
