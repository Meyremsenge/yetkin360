import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SikayetlerPage from "@/app/admin/sikayetler/page";
import {
  getComplaintEvidenceUrl,
  getComplaintQueue,
  resolveComplaint,
  type AdminComplaint,
} from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/errors";
import { useSession } from "@/lib/session/use-session";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/complaints", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/complaints")>()),
  getComplaintEvidenceUrl: vi.fn(),
  getComplaintQueue: vi.fn(),
  resolveComplaint: vi.fn(),
}));

function item(overrides: Partial<AdminComplaint>): AdminComplaint {
  return {
    id: "cmp-1",
    engagement_id: "eng-1",
    engagement_title: "Backend Stajı",
    engagement_status: "ACTIVE",
    talent_name: "Ayşe Yılmaz",
    organization_id: "org-1",
    organization_name: "Lale Yazılım A.Ş.",
    organization_upheld_count: 0,
    category: "TASK_APPROVAL",
    description: "Görevlerim üç haftadır onaylanmıyor.",
    has_evidence: false,
    status: "OPEN",
    decision_note: null,
    decided_at: null,
    created_at: "2026-10-01T00:00:00Z",
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SikayetlerPage />
    </QueryClientProvider>,
  );
}

describe("SikayetlerPage (/admin/sikayetler)", () => {
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

  it("açık şikayeti öğrenci, kuruluş, çalışma, konu ve açıklamayla listeler", async () => {
    vi.mocked(getComplaintQueue).mockResolvedValue([item({ has_evidence: true })]);

    renderPage();

    const row = await screen.findByTestId("admin-complaint");
    expect(getComplaintQueue).toHaveBeenCalledWith("OPEN");
    expect(within(row).getByText("Ayşe Yılmaz")).toBeTruthy();
    expect(within(row).getByText("Lale Yazılım A.Ş.")).toBeTruthy();
    expect(row.textContent).toContain("Backend Stajı");
    expect(within(row).getByText("Görevim onaylanmıyor")).toBeTruthy();
    expect(within(row).getByText("Görevlerim üç haftadır onaylanmıyor.")).toBeTruthy();
    expect(within(row).getByText("Belge eklendi")).toBeTruthy();
    expect(within(row).queryByTestId("complaint-stamp")).toBeNull();
  });

  it("daha önce haklı bulunan şikayeti olan kuruluş damga ve sayaçla gösterilir", async () => {
    vi.mocked(getComplaintQueue).mockResolvedValue([item({ organization_upheld_count: 2 })]);

    renderPage();

    const stamp = await screen.findByTestId("complaint-stamp");
    expect(stamp.textContent).toBe("Kasıtlı doğrulamama · 2");
  });

  it("kuyruk boşsa ne olacağını söyleyen boş durum gösterilir", async () => {
    vi.mocked(getComplaintQueue).mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText("Bekleyen şikayet yok.")).toBeTruthy();
  });

  it("'Haklı bul' önce onay ister; onaylanınca kararı notla birlikte gönderir", async () => {
    vi.mocked(getComplaintQueue).mockResolvedValue([item({})]);
    vi.mocked(resolveComplaint).mockResolvedValue(item({ status: "UPHELD" }));
    const user = userEvent.setup();
    renderPage();

    const row = await screen.findByTestId("admin-complaint");
    await user.type(within(row).getByLabelText("Karar notu (isteğe bağlı)"), "Üç hatırlatmaya yanıt yok.");
    await user.click(within(row).getByRole("button", { name: "Ayşe Yılmaz, Backend Stajı: Haklı bul" }));

    expect(resolveComplaint).not.toHaveBeenCalled();
    expect(within(row).getByText(/kuruluşun sayacına eklenecek/)).toBeTruthy();

    await user.click(within(row).getByRole("button", { name: "Kararı onayla" }));

    await waitFor(() => {
      expect(resolveComplaint).toHaveBeenCalledWith("cmp-1", "UPHELD", "Üç hatırlatmaya yanıt yok.");
    });
  });

  it("'Kapat' notsuz da gönderilebilir; 'Vazgeç' hiçbir şey göndermez", async () => {
    vi.mocked(getComplaintQueue).mockResolvedValue([item({})]);
    vi.mocked(resolveComplaint).mockResolvedValue(item({ status: "DISMISSED" }));
    const user = userEvent.setup();
    renderPage();

    const row = await screen.findByTestId("admin-complaint");
    await user.click(within(row).getByRole("button", { name: "Ayşe Yılmaz, Backend Stajı: Kapat" }));
    await user.click(within(row).getByRole("button", { name: "Vazgeç" }));
    expect(resolveComplaint).not.toHaveBeenCalled();

    await user.click(within(row).getByRole("button", { name: "Ayşe Yılmaz, Backend Stajı: Kapat" }));
    await user.click(within(row).getByRole("button", { name: "Kararı onayla" }));

    await waitFor(() => {
      expect(resolveComplaint).toHaveBeenCalledWith("cmp-1", "DISMISSED", undefined);
    });
  });

  it("sekme değişince o durumdaki şikayetler istenir; karara bağlananlarda karar düğmesi olmaz", async () => {
    vi.mocked(getComplaintQueue).mockImplementation(async (status) =>
      status === "UPHELD"
        ? [item({ status: "UPHELD", decided_at: "2026-10-05T00:00:00Z", decision_note: "Kanıt yeterli.", organization_upheld_count: 1 })]
        : [],
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("tab", { name: "Haklı bulunan" }));

    const row = await screen.findByTestId("admin-complaint");
    expect(getComplaintQueue).toHaveBeenCalledWith("UPHELD");
    expect(row.textContent).toContain("Kanıt yeterli.");
    expect(within(row).getByTestId("complaint-stamp").textContent).toBe("Kasıtlı doğrulamama · 1");
    expect(within(row).queryByRole("button", { name: /Haklı bul/ })).toBeNull();
  });

  it("şikayet başkası tarafından karara bağlanmışsa bunu söyler", async () => {
    vi.mocked(getComplaintQueue).mockResolvedValue([item({})]);
    vi.mocked(resolveComplaint).mockRejectedValue(
      new ApiError({ status: 409, code: "NOT_OPEN", message: "x", requestId: null }),
    );
    const user = userEvent.setup();
    renderPage();

    const row = await screen.findByTestId("admin-complaint");
    await user.click(within(row).getByRole("button", { name: /Kapat$/ }));
    await user.click(within(row).getByRole("button", { name: "Kararı onayla" }));

    expect(await screen.findByText("Bu şikayet zaten karara bağlanmış.")).toBeTruthy();
  });

  it("yetkisiz kullanıcıda (404) kaynak bulunamadı mesajı gösterilir", async () => {
    vi.mocked(getComplaintQueue).mockRejectedValue(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null }),
    );

    renderPage();

    expect(await screen.findByText("Kaynak bulunamadı.")).toBeTruthy();
  });

  describe("eklenen belge", () => {
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    it("belgesiz şikayette 'Belgeyi aç' düğmesi yoktur", async () => {
      vi.mocked(getComplaintQueue).mockResolvedValue([item({})]);

      renderPage();

      await screen.findByTestId("admin-complaint");
      expect(screen.queryByRole("button", { name: /belgeyi aç/ })).toBeNull();
    });

    function stubTab() {
      const tab = { opener: {} as unknown, location: { href: "" }, close: vi.fn() };
      const open = vi.fn(() => tab);
      vi.stubGlobal("open", open);
      return { tab, open };
    }

    it("'Belgeyi aç' bağlantıyı ancak tıklanınca ister ve yeni sekmede açar", async () => {
      const { tab, open } = stubTab();
      vi.mocked(getComplaintQueue).mockResolvedValue([item({ has_evidence: true })]);
      vi.mocked(getComplaintEvidenceUrl).mockResolvedValue("https://storage.example.test/doc.pdf?sig=x");
      const user = userEvent.setup();
      renderPage();

      const button = await screen.findByRole("button", { name: "Ayşe Yılmaz, Backend Stajı: eklenen belgeyi aç" });
      expect(getComplaintEvidenceUrl).not.toHaveBeenCalled();

      await user.click(button);

      await waitFor(() => {
        expect(getComplaintEvidenceUrl).toHaveBeenCalledWith("cmp-1");
        expect(tab.location.href).toBe("https://storage.example.test/doc.pdf?sig=x");
      });
      expect(open).toHaveBeenCalledWith("", "_blank");
      // The file's origin gets no handle on the admin page.
      expect(tab.opener).toBeNull();
    });

    it("belge açılamıyorsa nedenini söyler ve açılan boş sekmeyi kapatır", async () => {
      const { tab } = stubTab();
      vi.mocked(getComplaintQueue).mockResolvedValue([item({ has_evidence: true })]);
      vi.mocked(getComplaintEvidenceUrl).mockRejectedValue(
        new ApiError({ status: 409, code: "EVIDENCE_CONTENT_CHANGED", message: "x", requestId: null }),
      );
      const user = userEvent.setup();
      renderPage();

      await user.click(await screen.findByRole("button", { name: /eklenen belgeyi aç/ }));

      expect(await screen.findByText(/dosya taramadan sonra değişmiş/)).toBeTruthy();
      expect(tab.close).toHaveBeenCalled();
      expect(tab.location.href).toBe("");
    });
  });
});
