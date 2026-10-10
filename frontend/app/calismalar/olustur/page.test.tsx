import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import CalismaOlusturPage from "./page";
import { createEngagement } from "@/lib/api/engagements";
import { listApprovers } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
}));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/organizations", () => ({ listApprovers: vi.fn() }));
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
    vi.mocked(listApprovers).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("organization_id query param yoksa eksik link mesajı gösterilir, form render edilmez", () => {
    mockSearchParams(null);
    mockSessionWithTalent("talent-1");

    renderWithQueryClient(<CalismaOlusturPage />);

    expect(screen.getByText(/Önce bir kuruluş seçmeniz gerekiyor/)).toBeTruthy();
    expect(screen.queryByLabelText("Başlık")).toBeNull();
  });

  it("talent_profile yoksa (öğrenci değil) ilgili mesaj gösterilir", () => {
    mockSearchParams("org-1");
    mockSessionWithTalent(undefined);

    renderWithQueryClient(<CalismaOlusturPage />);

    expect(screen.getByText(/yalnızca bireysel hesaplar için/)).toBeTruthy();
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
      expect(screen.getByText("Bu kuruluş bulunamadı. Kuruluşunuzdan doğru bağlantıyı isteyin.")).toBeTruthy();
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

  describe("SPRINT D1: onaylayıcı seçimi", () => {
    const approvers = [
      { user_id: "user-mehmet", display_name: "Mehmet Kaya", unit: "Yazılım" },
      { user_id: "user-zeynep", display_name: "Zeynep Ak", unit: null },
      // The student is also a member of this organization: never offered to themselves.
      { user_id: "user-1", display_name: "Ayşe Yılmaz", unit: "Staj" },
    ];
    const created = {
      id: "eng-new-2", talent_id: "talent-1", organization_id: "org-1", institution_id: null,
      kind: "INTERNSHIP" as const, title: "x", status: "DRAFT" as const, version: 1, reason: null,
      created_at: "2026-10-10T00:00:00Z", updated_at: "2026-10-10T00:00:00Z",
    };

    it("liste 'Ad Soyad · Birim' etiketleriyle gösterilir, varsayılan genel seçenektir, kendisi listede yoktur", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockResolvedValueOnce(approvers);

      renderWithQueryClient(<CalismaOlusturPage />);

      const select = (await screen.findByLabelText(messages.calismaOlustur.supervisorLabel)) as HTMLSelectElement;
      const labels = Array.from(select.options).map((option) => option.textContent);
      expect(labels).toEqual([messages.calismaOlustur.supervisorDefault, "Mehmet Kaya · Yazılım", "Zeynep Ak"]);
      expect(select.value).toBe("");
      expect(listApprovers).toHaveBeenCalledWith("org-1");
    });

    it("seçilen kişi supervisor_user_id olarak gönderilir", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockResolvedValueOnce(approvers);
      vi.mocked(createEngagement).mockResolvedValueOnce(created);

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await user.selectOptions(
        await screen.findByLabelText(messages.calismaOlustur.supervisorLabel),
        "user-mehmet"
      );
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByText("Oluştur"));

      await waitFor(() => {
        expect(createEngagement).toHaveBeenCalledWith(expect.objectContaining({ supervisor_user_id: "user-mehmet" }));
      });
    });

    it("genel seçenekte supervisor_user_id gönderilmez", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockResolvedValueOnce(approvers);
      vi.mocked(createEngagement).mockResolvedValueOnce(created);

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await screen.findByLabelText(messages.calismaOlustur.supervisorLabel);
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByText("Oluştur"));

      await waitFor(() => expect(createEngagement).toHaveBeenCalled());
      expect(vi.mocked(createEngagement).mock.calls[0][0].supervisor_user_id).toBeUndefined();
    });

    it("liste boşsa (ya da yalnız kendisi varsa) alan gösterilmez", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockResolvedValueOnce([approvers[2]]);

      renderWithQueryClient(<CalismaOlusturPage />);

      await waitFor(() => expect(listApprovers).toHaveBeenCalled());
      expect(screen.getByLabelText("Başlık")).toBeTruthy();
      expect(screen.queryByLabelText(messages.calismaOlustur.supervisorLabel)).toBeNull();
    });

    it("liste alınamazsa (ör. 404) alan gösterilmez, form yine çalışır", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockRejectedValueOnce(
        new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
      );

      renderWithQueryClient(<CalismaOlusturPage />);

      await waitFor(() => expect(listApprovers).toHaveBeenCalled());
      expect(screen.getByLabelText("Başlık")).toBeTruthy();
      expect(screen.queryByLabelText(messages.calismaOlustur.supervisorLabel)).toBeNull();
    });

    it("onaylayıcı seçiliyken 404 gelirse onaylayıcının artık uygun olmadığı söylenir", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockResolvedValue(approvers);
      vi.mocked(createEngagement).mockRejectedValueOnce(
        new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await user.selectOptions(
        await screen.findByLabelText(messages.calismaOlustur.supervisorLabel),
        "user-zeynep"
      );
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByText("Oluştur"));

      expect(await screen.findByText(messages.calismaOlustur.supervisorUnavailableError)).toBeTruthy();
    });
  });
});
