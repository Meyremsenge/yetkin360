import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CalismalarPage from "@/app/calismalar/page";
import { useSession } from "@/lib/session/use-session";
import { listEngagements, type EngagementSummary } from "@/lib/api/engagements";

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

type SessionShape = {
  organizations?: { id: string; name: string }[];
  institutions?: { id: string; name: string }[];
  talent_profile?: { id: string } | null;
};

// Default: a student. Organization/institution members get the review view.
function mockSession({
  organizations = [],
  institutions = [],
  talent_profile = { id: "talent-1" },
}: SessionShape = {}) {
  vi.mocked(useSession).mockReturnValue({
    data: {
      user: { id: "user-1", email: "user@test.com" },
      organizations,
      institutions,
      talent_profile,
    },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>);
}

function summary(overrides: Partial<EngagementSummary>): EngagementSummary {
  return {
    id: "eng-1",
    title: "Frontend Stajı",
    kind: "INTERNSHIP",
    status: "ACTIVE",
    organization_id: "org-1",
    institution_id: null,
    organization_name: "Acme A.Ş.",
    version: 1,
    updated_at: "2026-09-01T00:00:00Z",
    talent_id: "talent-1",
    talent_name: "Ayşe Yılmaz",
    ...overrides,
  };
}

/**
 * YET-95 (PLAN 2.11): Engagement listesi ekranı (GET /engagements — mock).
 */
describe("CalismalarPage (/calismalar)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSession();
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
          talent_id: "talent-1",
          talent_name: "Ayşe Yılmaz",
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
          talent_id: "talent-1",
          talent_name: "Ayşe Yılmaz",
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
          talent_id: "talent-1",
          talent_name: "Ayşe Yılmaz",
        },
      ],
    });

    renderWithQueryClient(<CalismalarPage />);

    await waitFor(() => {
      expect(screen.getByText("Değerlendirildi")).toBeTruthy();
    });
  });

  describe("kurum/kuruluş görünümü", () => {
    const ORG = [{ id: "org-1", name: "Acme A.Ş." }];
    const INST = [{ id: "inst-1", name: "Bilgi Üniversitesi" }];

    it("kuruluş üyesi 'Öğrenci çalışmaları' başlığını görür, 'Yeni Çalışma' düğmesini görmez", async () => {
      mockSession({ organizations: ORG, talent_profile: null });
      vi.mocked(listEngagements).mockResolvedValueOnce({ items: [summary({})] });

      renderWithQueryClient(<CalismalarPage />);

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 1, name: "Öğrenci çalışmaları" })).toBeTruthy();
      });
      expect(screen.queryByRole("link", { name: "Yeni Çalışma" })).toBeNull();
      expect(screen.queryByRole("group", { name: "Çalışma görünümü" })).toBeNull();
    });

    it("kuruluş üyesi öğrenci adını ve onayladığı çalışmayı görür", async () => {
      mockSession({ organizations: ORG, talent_profile: null });
      vi.mocked(listEngagements).mockResolvedValueOnce({ items: [summary({})] });

      renderWithQueryClient(<CalismalarPage />);

      const card = await screen.findByTestId("review-approved-card");
      expect(within(card).getByText("Ayşe Yılmaz")).toBeTruthy();
      expect(within(card).getByText("Frontend Stajı")).toBeTruthy();
      expect(within(card).getByText("Öğrenci görev ve kanıt ekliyor")).toBeTruthy();
      expect(card.getAttribute("href")).toBe("/calismalar/eng-1");
    });

    it("koordinatör için onay bekleyen çalışma 'Sizden işlem bekleyenler'de listelenir", async () => {
      mockSession({ institutions: INST, talent_profile: null });
      vi.mocked(listEngagements).mockResolvedValueOnce({
        items: [summary({ id: "eng-2", status: "PENDING_APPROVAL", institution_id: "inst-1" })],
      });

      renderWithQueryClient(<CalismalarPage />);

      const row = await screen.findByTestId("review-awaiting-row");
      expect(within(row).getByText("Ayşe Yılmaz")).toBeTruthy();
      expect(within(row).getByText("Başlatma onayınızı bekliyor")).toBeTruthy();
      expect(within(row).getByRole("link").getAttribute("href")).toBe("/calismalar/eng-2");
      expect(screen.queryByTestId("review-approved-card")).toBeNull();
      expect(screen.getByText("Henüz onay verdiğiniz bir çalışma yok.")).toBeTruthy();
    });

    it("kuruluş üyesi için boş liste, ne olacağını söyleyen boş durumla gösterilir", async () => {
      mockSession({ organizations: ORG, talent_profile: null });
      vi.mocked(listEngagements).mockResolvedValueOnce({ items: [] });

      renderWithQueryClient(<CalismalarPage />);

      await waitFor(() => {
        expect(screen.getByText("Henüz size bağlı bir öğrenci çalışması yok.")).toBeTruthy();
      });
    });

    it("hem öğrenci hem kuruluş üyesi olan kullanıcı iki görünüm arasında geçer", async () => {
      mockSession({ organizations: ORG, talent_profile: { id: "talent-me" } });
      vi.mocked(listEngagements).mockResolvedValueOnce({
        items: [
          summary({ id: "eng-own", title: "Kendi Stajım", talent_id: "talent-me", organization_id: "org-9" }),
          summary({ id: "eng-student", title: "Öğrencinin Stajı", talent_id: "talent-2", talent_name: "Can Demir" }),
        ],
      });

      renderWithQueryClient(<CalismalarPage />);

      // Own view first: only the engagement the user is the student of.
      await waitFor(() => {
        expect(screen.getByText("Kendi Stajım")).toBeTruthy();
      });
      expect(screen.queryByText("Öğrencinin Stajı")).toBeNull();

      const switcher = screen.getByRole("group", { name: "Çalışma görünümü" });
      fireEvent.click(within(switcher).getByRole("button", { name: "Öğrenci çalışmaları" }));

      await waitFor(() => {
        expect(screen.getByText("Öğrencinin Stajı")).toBeTruthy();
      });
      expect(screen.getByText("Can Demir")).toBeTruthy();
      expect(screen.queryByText("Kendi Stajım")).toBeNull();
    });
  });
});
