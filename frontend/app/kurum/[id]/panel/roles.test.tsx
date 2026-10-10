import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KurumPanelPage from "./page";
import { useParams } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import {
  getCoordinatorDashboard,
  listInstitutionPartners,
  listInstitutionStudents,
  listPendingLinkRequests,
  type DashboardResponse,
} from "@/lib/api/institutions";
import { transitionEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

vi.mock("next/navigation", () => ({ useParams: vi.fn() }));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/engagements", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/engagements")>();
  return { ...actual, transitionEngagement: vi.fn() };
});
vi.mock("@/lib/api/institutions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/institutions")>();
  return {
    ...actual,
    getCoordinatorDashboard: vi.fn(),
    listPendingLinkRequests: vi.fn(),
    listInstitutionStudents: vi.fn(),
    listInstitutionPartners: vi.fn(),
  };
});

const t = messages.kurumPanel;

function sessionWithRole(role: string | undefined) {
  return {
    data: {
      user: { id: "user-1" },
      organizations: [],
      institutions: [{ id: "inst-1", name: "Galata Teknik Üniversitesi", ...(role ? { role } : {}) }],
      talent_profile: null,
    },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>;
}

const pending = {
  id: "eng-1",
  talent_id: "talent-1",
  organization_id: "org-1",
  talent_full_name: "Ayşe Yılmaz",
  organization_name: "Lale Yazılım",
  kind: "INTERNSHIP",
  version: 4,
  title: "Mobil Uygulama Stajı",
  started_on: "2026-09-01",
};

const dashboard: DashboardResponse = {
  institution_id: "inst-1",
  summary: { pending_approval: 1, pending_evaluation: 0, pending_attestation: 1 },
  pending_approval: [pending],
  pending_evaluation: [],
  pending_attestation: [
    {
      ...pending,
      id: "eng-2",
      title: "Veri Analizi Projesi",
      talent_full_name: "Mehmet Kaya",
      ended_on: "2026-09-30",
    },
  ],
  members: [
    { user_id: "u-1", email: "y***@galata.edu.tr", role: "ADMIN", joined_at: "2026-01-01T00:00:00Z" },
    { user_id: "u-2", email: "k***@galata.edu.tr", role: "COORDINATOR", joined_at: "2026-01-01T00:00:00Z" },
  ],
};

const approveName = t.approveOf.replace("{title}", pending.title);
const rejectName = t.rejectOf.replace("{title}", pending.title);

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <KurumPanelPage />
    </QueryClientProvider>
  );
}

/** Renders the panel and returns the approval section once the dashboard is in. */
async function approvalSection() {
  renderPage();
  await screen.findByText(pending.title);
  return document.getElementById("onay-bekleyen") as HTMLElement;
}

describe("KurumPanelPage — rol farkı ve satır içi onay (SPRINT E)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "inst-1" });
    vi.mocked(getCoordinatorDashboard).mockResolvedValue(dashboard);
    vi.mocked(listPendingLinkRequests).mockResolvedValue({ items: [] });
    vi.mocked(listInstitutionStudents).mockResolvedValue({ items: [] });
    vi.mocked(listInstitutionPartners).mockResolvedValue({ items: [] });
  });

  afterEach(() => {
    cleanup();
  });

  describe("Yönetici (ADMIN)", () => {
    beforeEach(() => {
      vi.mocked(useSession).mockReturnValue(sessionWithRole("ADMIN"));
    });

    it("AC-1: onay düğmeleri yok, kimin onayladığı açıkça yazar", async () => {
      const section = await approvalSection();
      expect(within(section).queryByRole("button", { name: approveName })).toBeNull();
      expect(within(section).queryByRole("button", { name: rejectName })).toBeNull();
      expect(within(section).getByText(t.adminApprovalNote)).toBeTruthy();
    });

    it("başlıkta rol rozeti ve açıklaması, davet formu görünür", async () => {
      await approvalSection();
      expect(screen.getByText(t.roleDescription.ADMIN)).toBeTruthy();
      expect(screen.getByLabelText(t.inviteEmailLabel)).toBeTruthy();
    });

    it("mühür bekleyen satırda Mühürle bağlantısı yok", async () => {
      await approvalSection();
      const section = document.getElementById("muhur-bekleyen") as HTMLElement;
      expect(within(section).getByText("Veri Analizi Projesi")).toBeTruthy();
      expect(within(section).queryByRole("link", { name: /mühürle/i })).toBeNull();
    });
  });

  describe("Koordinatör (COORDINATOR)", () => {
    beforeEach(() => {
      vi.mocked(useSession).mockReturnValue(sessionWithRole("COORDINATOR"));
    });

    it("AC-1: satır içi Onayla/Reddet var, davet formu yok", async () => {
      const section = await approvalSection();
      expect(within(section).getByRole("button", { name: approveName })).toBeTruthy();
      expect(within(section).getByRole("button", { name: rejectName })).toBeTruthy();
      expect(within(section).queryByText(t.adminApprovalNote)).toBeNull();
      expect(screen.queryByLabelText(t.inviteEmailLabel)).toBeNull();
      expect(screen.getByText(t.roleDescription.COORDINATOR)).toBeTruthy();
    });

    it("satır kişi ve kuruluş adını taşır, Tümünü gör /calismalar'a gider", async () => {
      const section = await approvalSection();
      expect(within(section).getByText("Ayşe Yılmaz · Lale Yazılım")).toBeTruthy();
      expect(within(section).getByRole("link", { name: t.seeAll }).getAttribute("href")).toBe("/calismalar");
    });

    it("Onayla → ACTIVE geçişi satırdaki version ile gönderilir, liste yenilenir", async () => {
      vi.mocked(transitionEngagement).mockResolvedValueOnce({} as Awaited<ReturnType<typeof transitionEngagement>>);
      const user = userEvent.setup();
      const section = await approvalSection();

      await user.click(within(section).getByRole("button", { name: approveName }));

      expect(transitionEngagement).toHaveBeenCalledWith("eng-1", { to_status: "ACTIVE", version: 4 });
      expect(await within(section).findByText(t.approvedMessage)).toBeTruthy();
      await waitFor(() => expect(getCoordinatorDashboard).toHaveBeenCalledTimes(2));
    });

    it("AC-2: Reddet gerekçesiz gönderilemez; gerekçeyle REJECTED gönderilir", async () => {
      vi.mocked(transitionEngagement).mockResolvedValueOnce({} as Awaited<ReturnType<typeof transitionEngagement>>);
      const user = userEvent.setup();
      const section = await approvalSection();

      await user.click(within(section).getByRole("button", { name: rejectName }));
      await user.click(within(section).getByRole("button", { name: t.rejectSubmit }));
      expect(within(section).getByRole("alert").textContent).toBe(t.rejectReasonRequired);
      expect(transitionEngagement).not.toHaveBeenCalled();

      await user.type(within(section).getByLabelText(t.rejectReasonLabel), "   ");
      await user.click(within(section).getByRole("button", { name: t.rejectSubmit }));
      expect(transitionEngagement).not.toHaveBeenCalled();

      await user.type(within(section).getByLabelText(t.rejectReasonLabel), "Kurum dışı çalışma");
      await user.click(within(section).getByRole("button", { name: t.rejectSubmit }));
      expect(transitionEngagement).toHaveBeenCalledWith("eng-1", {
        to_status: "REJECTED",
        version: 4,
        reason: "Kurum dışı çalışma",
      });
      expect(await within(section).findByText(t.rejectedMessage)).toBeTruthy();
    });

    it("409 → 'Kayıt değişti, liste yenilendi' ve liste yeniden çekilir", async () => {
      vi.mocked(transitionEngagement).mockRejectedValueOnce(
        new ApiError({ status: 409, code: "VERSION_CONFLICT", message: "Çakışma", requestId: null })
      );
      const user = userEvent.setup();
      const section = await approvalSection();

      await user.click(within(section).getByRole("button", { name: approveName }));

      expect(await within(section).findByText(t.conflictMessage)).toBeTruthy();
      await waitFor(() => expect(getCoordinatorDashboard).toHaveBeenCalledTimes(2));
    });

    it("mühür bekleyen satırda Mühürle çalışma sayfasına gider", async () => {
      await approvalSection();
      const section = document.getElementById("muhur-bekleyen") as HTMLElement;
      expect(within(section).getByText(t.pendingAttestationHint)).toBeTruthy();
      const seal = within(section).getByRole("link", {
        name: t.sealButtonOf.replace("{title}", "Veri Analizi Projesi"),
      });
      expect(seal.getAttribute("href")).toBe("/calismalar/eng-2#taniklik");
    });
  });

  describe("İş birlikleri ve rapor (AC-3)", () => {
    beforeEach(() => {
      vi.mocked(useSession).mockReturnValue(sessionWithRole("COORDINATOR"));
    });

    it("iş birlikleri sayılarıyla listelenir", async () => {
      vi.mocked(listInstitutionPartners).mockResolvedValue({
        items: [
          {
            organization_id: "org-1",
            organization_name: "Lale Yazılım",
            verification_level: "T3",
            student_count: 4,
            engagement_count: 6,
            verified_count: 2,
          },
        ],
      });
      renderPage();

      const section = (await screen.findByText(t.partnersTitle)).closest("section") as HTMLElement;
      expect(await within(section).findByText("Lale Yazılım")).toBeTruthy();
      expect(within(section).getByText("4 öğrenci")).toBeTruthy();
      expect(within(section).getByText("6 çalışma")).toBeTruthy();
      expect(within(section).getByText("2 mühürlü")).toBeTruthy();
    });

    it("iş birliği yoksa boş durum gösterir", async () => {
      renderPage();
      expect(await screen.findByText(t.partnersEmptyTitle)).toBeTruthy();
    });

    it("CSV rapor bağlantısı başlıkta, indirme olarak", async () => {
      renderPage();
      const link = (await screen.findByText(t.reportCsvButton)).closest("a") as HTMLAnchorElement;
      expect(link.getAttribute("href")).toMatch(/\/institutions\/inst-1\/report\.csv$/);
      expect(link.hasAttribute("download")).toBe(true);
    });
  });

  it("rol bilgisi yoksa (eski /me) önceki davranış: eylemler görünür, sunucu karar verir", async () => {
    vi.mocked(useSession).mockReturnValue(sessionWithRole(undefined));
    const section = await approvalSection();
    expect(within(section).getByRole("button", { name: approveName })).toBeTruthy();
    expect(screen.getByLabelText(t.inviteEmailLabel)).toBeTruthy();
  });
});
