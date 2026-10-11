import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import CalismaOlusturPage from "./page";
import { createEngagement, listOwnApprovalRecipients, transitionEngagement } from "@/lib/api/engagements";
import { listApprovers } from "@/lib/api/organizations";
import { getOrganizationShowcase } from "@/lib/api/public";
import { ApiError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
}));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/organizations", () => ({ listApprovers: vi.fn() }));
vi.mock("@/lib/api/public", () => ({ getOrganizationShowcase: vi.fn() }));
vi.mock("@/lib/api/engagements", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/engagements")>();
  return {
    ...actual,
    createEngagement: vi.fn(),
    transitionEngagement: vi.fn(),
    listOwnApprovalRecipients: vi.fn(),
  };
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
    vi.mocked(listOwnApprovalRecipients).mockResolvedValue([]);
    vi.mocked(transitionEngagement).mockResolvedValue({} as Awaited<ReturnType<typeof transitionEngagement>>);
    vi.mocked(getOrganizationShowcase).mockResolvedValue({
      id: "org-1", name: "Acme A.Ş.", verification_level: "T2", domain: "acme.com",
      showcase_enabled: false, stats: { verified_public_count: 0, institution_count: 0 }, experiences: [],
    });
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

  it("organization_id ve talent_profile varsa form render edilir — tür + başlık + seçili kuruluş", async () => {
    mockSearchParams("org-1");
    mockSessionWithTalent("talent-1");

    renderWithQueryClient(<CalismaOlusturPage />);

    const kinds = screen.getByRole("group", { name: "Tür" });
    expect(within(kinds).getAllByRole("radio")).toHaveLength(4);
    expect((within(kinds).getByLabelText(/Staj/) as HTMLInputElement).checked).toBe(true);
    expect(screen.getByLabelText("Başlık")).toBeTruthy();
    expect(await screen.findByText("Acme A.Ş.")).toBeTruthy();
    expect(getOrganizationShowcase).toHaveBeenCalledWith("org-1");
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
    await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

    await waitFor(() => {
      expect(createEngagement).toHaveBeenCalledWith({
        talent_id: "talent-1",
        organization_id: "org-1",
        kind: "INTERNSHIP",
        title: "Yeni Staj",
        institution_id: "inst-1",
      });
      // An internship with a school goes straight to the school for approval.
      expect(transitionEngagement).toHaveBeenCalledWith("eng-new-1", { to_status: "PENDING_APPROVAL", version: 1 });
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
    await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

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

    await user.click(screen.getByLabelText(/Yarı Zamanlı/));
    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

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
    await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

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
    await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

    await waitFor(() => {
      expect(screen.getByText("İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin.")).toBeTruthy();
    });
  });

  describe("SPRINT D1: onaylayıcı seçimi", () => {
    const approvers = [
      { user_id: "user-mehmet", display_name: "Mehmet Kaya", unit: "Yazılım", email_hint: "me•••@acme.com" },
      { user_id: "user-zeynep", display_name: "Zeynep Ak", unit: null, email_hint: "ze•••@acme.com" },
      // The student is also a member of this organization: never offered to themselves.
      { user_id: "user-1", display_name: "Ayşe Yılmaz", unit: "Staj", email_hint: "ay•••@acme.com" },
    ];
    const created = {
      id: "eng-new-2", talent_id: "talent-1", organization_id: "org-1", institution_id: null,
      kind: "INTERNSHIP" as const, title: "x", status: "DRAFT" as const, version: 1, reason: null,
      created_at: "2026-10-10T00:00:00Z", updated_at: "2026-10-10T00:00:00Z",
    };

    it("liste ad, birim ve maskeli e-postayla gösterilir, varsayılan genel seçenektir, kendisi listede yoktur", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockResolvedValueOnce(approvers);

      renderWithQueryClient(<CalismaOlusturPage />);

      const group = await screen.findByRole("group", { name: messages.calismaOlustur.supervisorLabel });
      const radios = within(group).getAllByRole("radio") as HTMLInputElement[];
      expect(radios.map((radio) => radio.value)).toEqual(["", "user-mehmet", "user-zeynep"]);
      expect(radios[0].checked).toBe(true);
      expect(within(group).getByText(messages.calismaOlustur.supervisorDefault)).toBeTruthy();
      expect(within(group).getByText("me•••@acme.com")).toBeTruthy();
      expect(within(group).queryByText("Ayşe Yılmaz")).toBeNull();
      expect(listApprovers).toHaveBeenCalledWith("org-1");
    });

    it("seçilen kişi supervisor_user_id olarak gönderilir", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1");
      vi.mocked(listApprovers).mockResolvedValueOnce(approvers);
      vi.mocked(createEngagement).mockResolvedValueOnce(created);

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await user.click(await screen.findByRole("radio", { name: /Mehmet Kaya/ }));
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

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

      await screen.findByRole("group", { name: messages.calismaOlustur.supervisorLabel });
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

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
      expect(screen.queryByRole("group", { name: messages.calismaOlustur.supervisorLabel })).toBeNull();
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
      expect(screen.queryByRole("group", { name: messages.calismaOlustur.supervisorLabel })).toBeNull();
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

      await user.click(await screen.findByRole("radio", { name: /Zeynep Ak/ }));
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: /^Oluştur ve/ }));

      expect(await screen.findByText(messages.calismaOlustur.supervisorUnavailableError)).toBeTruthy();
    });
  });

  describe("tek adımda gönderme ve okul onayı", () => {
    const created = {
      id: "eng-9", talent_id: "talent-1", organization_id: "org-1", institution_id: null,
      kind: "INTERNSHIP" as const, title: "x", status: "DRAFT" as const, version: 1, reason: null,
      created_at: "2026-10-11T00:00:00Z", updated_at: "2026-10-11T00:00:00Z",
    };
    const coordinators = [
      { user_id: "u-kerem", display_name: "Kerem Taşkın", email_hint: "ke•••@cinaralti.edu.test" },
    ];

    it("staj + okul: koordinatör maskeli e-postayla listelenir, seçilen notify_user_ids ile gider", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1", "inst-1");
      vi.mocked(listOwnApprovalRecipients).mockResolvedValueOnce(coordinators);
      vi.mocked(createEngagement).mockResolvedValueOnce(created);

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      const group = await screen.findByRole("group", { name: messages.calismaOlustur.schoolLegend });
      expect(await within(group).findByText("ke•••@cinaralti.edu.test")).toBeTruthy();
      await user.click(within(group).getByRole("radio", { name: /Kerem Taşkın/ }));
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: "Oluştur ve onaya gönder" }));

      await waitFor(() => {
        expect(transitionEngagement).toHaveBeenCalledWith("eng-9", {
          to_status: "PENDING_APPROVAL",
          version: 1,
          notify_user_ids: ["u-kerem"],
        });
        expect(mockPush).toHaveBeenCalledWith("/calismalar/eng-9");
      });
    });

    it("yarı zamanlı + okul: okul bağlanmaz, çalışma hemen başlatılır", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1", "inst-1");
      vi.mocked(createEngagement).mockResolvedValueOnce({ ...created, kind: "PART_TIME" });

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await user.click(screen.getByLabelText(/Yarı Zamanlı/));
      expect(screen.queryByRole("group", { name: messages.calismaOlustur.schoolLegend })).toBeNull();
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: "Oluştur ve başlat" }));

      await waitFor(() => {
        expect(createEngagement).toHaveBeenCalledWith(
          expect.objectContaining({ kind: "PART_TIME", institution_id: undefined })
        );
        expect(transitionEngagement).toHaveBeenCalledWith("eng-9", { to_status: "ACTIVE", version: 1 });
      });
    });

    it("yarı zamanlıda 'okulum da onaylasın' işaretlenirse okul onayına gider", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1", "inst-1");
      vi.mocked(createEngagement).mockResolvedValueOnce({ ...created, kind: "PART_TIME" });

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await user.click(screen.getByLabelText(/Yarı Zamanlı/));
      await user.click(screen.getByRole("checkbox", { name: new RegExp(messages.calismaOlustur.schoolOptIn) }));
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: "Oluştur ve onaya gönder" }));

      await waitFor(() => {
        expect(createEngagement).toHaveBeenCalledWith(expect.objectContaining({ institution_id: "inst-1" }));
        expect(transitionEngagement).toHaveBeenCalledWith("eng-9", { to_status: "PENDING_APPROVAL", version: 1 });
      });
    });

    it("okulu olmayan kullanıcı: okul sorusu yok, staj da hemen başlatılır", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1", null);
      vi.mocked(createEngagement).mockResolvedValueOnce(created);

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      expect(screen.getByText(messages.calismaOlustur.noSchoolNote)).toBeTruthy();
      expect(screen.queryByRole("checkbox")).toBeNull();
      expect(listOwnApprovalRecipients).not.toHaveBeenCalled();
      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: "Oluştur ve başlat" }));

      await waitFor(() => {
        expect(transitionEngagement).toHaveBeenCalledWith("eng-9", { to_status: "ACTIVE", version: 1 });
      });
    });

    it("'Taslak olarak kaydet' yalnız oluşturur, göndermez", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1", "inst-1");
      vi.mocked(createEngagement).mockResolvedValueOnce(created);

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: "Taslak olarak kaydet" }));

      await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/calismalar/eng-9"));
      expect(transitionEngagement).not.toHaveBeenCalled();
    });

    it("oluşturulup gönderilemezse taslağa bağlantı verilir ve ikinci kez oluşturulmaz", async () => {
      mockSearchParams("org-1");
      mockSessionWithTalent("talent-1", "inst-1");
      vi.mocked(createEngagement).mockResolvedValueOnce(created);
      vi.mocked(transitionEngagement).mockRejectedValueOnce(
        new ApiError({ status: 500, code: "INTERNAL", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<CalismaOlusturPage />);

      await user.type(screen.getByLabelText("Başlık"), "x");
      await user.click(screen.getByRole("button", { name: "Oluştur ve onaya gönder" }));

      expect(await screen.findByText(messages.calismaOlustur.sendFailedAfterCreate)).toBeTruthy();
      expect(screen.getByRole("link", { name: messages.calismaOlustur.openDraft }).getAttribute("href")).toBe(
        "/calismalar/eng-9"
      );
      expect((screen.getByRole("button", { name: "Oluştur ve onaya gönder" }) as HTMLButtonElement).disabled).toBe(true);
      expect(createEngagement).toHaveBeenCalledTimes(1);
      expect(mockPush).not.toHaveBeenCalled();
    });
  });
});
