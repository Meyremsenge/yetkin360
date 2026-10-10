import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CalismaDetayPage from "@/app/calismalar/[id]/page";
import messages from "@/messages/tr.json";
import { useSession } from "@/lib/session/use-session";
import { useParams } from "next/navigation";
import { getEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";
import { makeViewer } from "@/lib/api/engagements.fixtures";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/engagements", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/engagements")>();
  return {
    ...actual,
    getEngagement: vi.fn(),
    transitionEngagement: vi.fn(),
  };
});
vi.mock("@/lib/api/deliverables", () => ({ createDeliverable: vi.fn() }));
vi.mock("@/lib/api/attestations", () => ({ createAttestation: vi.fn(), revokeAttestation: vi.fn() }));
vi.mock("@/lib/api/tasks", () => ({ createTask: vi.fn() }));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const baseEngagement: EngagementDetail = {
  id: "eng-1",
  title: "Yaz Kısa Projesi",
  kind: "SHORT_PROJECT",
  status: "ACTIVE",
  organization_name: "Bulut Sistemleri Ltd.",
  talent_id: "talent-1",
  organization_id: "org-1",
  institution_id: null,
  reason: null,
  version: 2,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-18T14:30:00Z",
  tasks: [{ id: "task-1", title: "API şeması", status: "DONE", verified: true }],
  deliverables: [],
  attestations: [],
  // The student on their own ACTIVE engagement (server-computed).
  supervisor: null,
  viewer: makeViewer({ relation: "SUBJECT", can_add_task: true, can_add_deliverable: true }),
};

const orgAdminViewer = makeViewer({
  relation: "ORG_ADMIN",
  allowed_transitions: ["CANCELLED", "PENDING_EVALUATION"],
  reason_required: ["CANCELLED"],
  can_add_task: true,
});

/**
 * YET-96 (PLAN 2.11): Engagement detay ekranı + available_transitions[] butonları.
 */
describe("CalismaDetayPage (/calismalar/[id])", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "eng-1" });
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
  });

  afterEach(() => {
    cleanup();
  });

  it("yüklenirken 'Yükleniyor...' gösterir", () => {
    vi.mocked(getEngagement).mockReturnValue(new Promise(() => {}));

    renderWithQueryClient(<CalismaDetayPage />);

    expect(screen.getByText("Yükleniyor...")).toBeTruthy();
  });

  it("404 ApiError → 'Çalışma bulunamadı.' gösterir", async () => {
    vi.mocked(getEngagement).mockRejectedValueOnce(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "Engagement bulunamadı.", requestId: null })
    );

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Çalışma bulunamadı.")).toBeTruthy();
    });
  });

  it("genel hata → 'Çalışma yüklenemedi.' gösterir", async () => {
    vi.mocked(getEngagement).mockRejectedValueOnce(new Error("boom"));

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Çalışma yüklenemedi.")).toBeTruthy();
    });
  });

  it("başarılı yüklemede başlık, durum, görevler ve durum geçiş butonları gösterilir", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({ ...baseEngagement, viewer: orgAdminViewer });

    const { container } = renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy();
      expect(screen.getByText("Aktif")).toBeTruthy();
      expect(container.textContent).toContain("API şeması");
      expect(container.textContent).toContain("Tamamlandı");
      expect(screen.getByText("Henüz çıktı yüklenmemiş.")).toBeTruthy();
      // viewer.allowed_transitions: CANCELLED, PENDING_EVALUATION
      expect(screen.getByText("İptal Et")).toBeTruthy();
      expect(screen.getByText("Değerlendirmeye Gönder")).toBeTruthy();
    });
  });

  it("SPRINT R: mühürlü kayıtta koordinatör 'Profilde gör' ve kanıt ekleme formunu görmez", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "VERIFIED",
      deliverables: [{ id: "d-1", title: "API raporu", submitted_at: "2026-10-01T00:00:00Z" }],
      viewer: makeViewer({ relation: "COORDINATOR" }),
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => expect(screen.getByText(messages.calismalar.detail.verifiedTextOther)).toBeTruthy());
    expect(screen.queryByText(messages.calismalar.detail.verifiedLink)).toBeNull();
    expect(screen.queryByText(messages.calismalar.evidenceUploadLabel)).toBeNull();
  });

  it("SPRINT R: öğrenci mühürlü kaydında 'Profilde gör' ve kanıt ekleme formunu görür", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "VERIFIED",
      deliverables: [{ id: "d-1", title: "API raporu", submitted_at: "2026-10-01T00:00:00Z" }],
      viewer: makeViewer({ relation: "SUBJECT" }),
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => expect(screen.getByText(messages.calismalar.detail.verifiedLink)).toBeTruthy());
    expect(screen.getByText(messages.calismalar.detail.verifiedText)).toBeTruthy();
    expect(screen.getByText(messages.calismalar.evidenceUploadLabel)).toBeTruthy();
  });

  it("SPRINT D1: onaylayıcı varsa başlıkta 'Onaylayıcı: Ad · Birim' gösterilir", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      supervisor: { user_id: "user-mehmet", display_name: "Mehmet Kaya", unit: "Yazılım" },
    });

    const { container } = renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(container.textContent).toContain("Onaylayıcı: Mehmet Kaya · Yazılım");
    });
  });

  it("SPRINT D1: onaylayıcı yoksa satır gösterilmez", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce(baseEngagement);

    const { container } = renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy());
    expect(container.textContent).not.toContain("Onaylayıcı:");
  });

  it("reddedilmiş/iptal gerekçesi (reason) varsa gösterilir", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "REJECTED",
      reason: "Kontenjan dolduğu için reddedildi.",
    });

    const { container } = renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(container.textContent).toContain("Kontenjan dolduğu için reddedildi.");
    });
  });

  it("viewer.can_evaluate ise 'Değerlendirme Formu' linki gösterilir", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "PENDING_EVALUATION",
      viewer: makeViewer({ relation: "ORG_MEMBER", can_evaluate: true }),
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      const link = screen.getByText("Değerlendirme Formu").closest("a");
      expect(link?.getAttribute("href")).toBe("/calismalar/eng-1/degerlendirme");
    });
  });

  it("SPRINT A: öğrenci PENDING_EVALUATION'da 'Değerlendirme Formu' linkini görmez", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "PENDING_EVALUATION",
      viewer: makeViewer({ relation: "SUBJECT" }),
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy();
    });
    expect(screen.queryByText("Değerlendirme Formu")).toBeNull();
  });

  // YET-202/ENT-01
  it("ACTIVE durumunda teslim (deliverable) ekleme formu gösterilir, tanıklık formu gösterilmez", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce(baseEngagement); // status: ACTIVE

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yeni Çıktı Ekle")).toBeTruthy();
    });
    expect(screen.queryByText("Tanıklık Ver")).toBeNull();
  });

  it("viewer.can_attest ise tanıklık formu gösterilir, teslim ekleme formu gösterilmez", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "EVALUATED",
      viewer: makeViewer({ relation: "COORDINATOR", can_attest: true }),
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Tanıklık Ver")).toBeTruthy();
    });
    expect(screen.queryByText("Yeni Çıktı Ekle")).toBeNull();
  });

  it("terminal durumda (REJECTED) ne teslim ne tanıklık formu gösterilir", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "REJECTED",
      viewer: makeViewer({ relation: "SUBJECT" }),
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy();
    });
    expect(screen.queryByText("Yeni Çıktı Ekle")).toBeNull();
    expect(screen.queryByText("Tanıklık Ver")).toBeNull();
  });

  it("AC-4: hiçbir izni olmayan izleyiciye (ör. kurum yöneticisi) eylem düğmesi/formu gösterilmez", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      tasks: [{ id: "task-2", title: "Öğrencinin görevi", status: "PLANNED", verified: false }],
      viewer: makeViewer({ relation: "INSTITUTION_ADMIN" }),
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy();
    });
    for (const label of Object.values(messages.calismalar.transitionAction)) {
      expect(screen.queryByRole("button", { name: label })).toBeNull();
    }
    expect(screen.queryByRole("button", { name: /görevini onayla/ })).toBeNull();
    expect(screen.queryByText("Yeni Görev Ekle")).toBeNull();
    expect(screen.queryByText("Yeni Çıktı Ekle")).toBeNull();
    expect(screen.queryByText("Değerlendirme Formu")).toBeNull();
    expect(screen.queryByText("Tanıklık Ver")).toBeNull();
  });

  it("YET-202/ENT-01: ACTIVE durumunda görev ekleme formu gösterilir", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce(baseEngagement); // status: ACTIVE

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yeni Görev Ekle")).toBeTruthy();
    });
  });

  it("YET-202/ENT-01: attestations[] doluysa listelenir; tanığın kendisi Geri Çek butonunu görür", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "VERIFIED",
      attestations: [
        {
          id: "att-1",
          claim_type: "COMPETENCE",
          requested_claim_type: "COMPETENCE",
          attestor_user_id: "user-1",
          created_at: "2026-09-27T10:00:00Z",
          revoked_at: null,
          revoke_reason: null,
        },
      ],
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yetkinlik")).toBeTruthy(); // claimType.COMPETENCE etiketi
      expect(screen.getByText("Geri Çek")).toBeTruthy();
    });
    expect(screen.queryByText("Henüz tanıklık yok.")).toBeNull();
  });

  // UX only: the server rejects non-attestors anyway; the form is hidden so a
  // student never sees an action they cannot take.
  it("tanık olmayan kullanıcı (ör. öğrenci) Geri Çek formunu görmez, tanıklık yine listelenir", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "VERIFIED",
      attestations: [
        {
          id: "att-1",
          claim_type: "COMPETENCE",
          requested_claim_type: "COMPETENCE",
          attestor_user_id: "user-9",
          created_at: "2026-09-27T10:00:00Z",
          revoked_at: null,
          revoke_reason: null,
        },
      ],
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yetkinlik")).toBeTruthy();
    });
    expect(screen.queryByText("Geri Çek")).toBeNull();
    expect(screen.queryByLabelText("Geri çekme gerekçesi")).toBeNull();
  });

  it("geri çekilmiş tanıklığın gerekçesi tanık olmayan kullanıcıya da görünür", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...baseEngagement,
      status: "VERIFIED",
      attestations: [
        {
          id: "att-1",
          claim_type: "COMPETENCE",
          requested_claim_type: "COMPETENCE",
          attestor_user_id: "user-9",
          created_at: "2026-09-27T10:00:00Z",
          revoked_at: "2026-09-28T10:00:00Z",
          revoke_reason: "Yanlış girilmiş",
        },
      ],
    });

    renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Geri çekildi: Yanlış girilmiş")).toBeTruthy();
    });
    expect(screen.queryByText("Geri Çek")).toBeNull();
  });

  describe("şikayet bağlantısı (sunucunun hesapladığı viewer.relation)", () => {
    const reportLink = () => screen.queryByRole("link", { name: messages.complaints.reportAction });

    it("öğrenci (SUBJECT) yanıtsız onayda kuruma şikayet bağlantısını görür", async () => {
      vi.mocked(getEngagement).mockResolvedValueOnce({ ...baseEngagement, status: "PENDING_APPROVAL" });

      renderWithQueryClient(<CalismaDetayPage />);

      const link = await screen.findByRole("link", { name: messages.complaints.reportAction });
      expect(link.getAttribute("href")).toContain("subject_id=eng-1");
      expect(screen.getByText(messages.complaints.reportHint)).toBeTruthy();
    });

    it("öğrenci (SUBJECT) yanıtsız değerlendirmede kuruluşa şikayet bağlantısını görür", async () => {
      vi.mocked(getEngagement).mockResolvedValueOnce({ ...baseEngagement, status: "PENDING_EVALUATION" });

      renderWithQueryClient(<CalismaDetayPage />);

      const link = await screen.findByRole("link", { name: messages.complaints.reportAction });
      expect(link.getAttribute("href")).toBe("/sikayetlerim/yeni?subject_type=ENGAGEMENT&subject_id=eng-1");
      expect(screen.getByText(messages.complaints.reportHintEvaluation)).toBeTruthy();
    });

    it.each(["PENDING_APPROVAL", "PENDING_EVALUATION"] as const)(
      "öğrenci olmayan izleyici (ORG_ADMIN) %s durumunda bağlantıyı görmez",
      async (status) => {
        vi.mocked(getEngagement).mockResolvedValueOnce({ ...baseEngagement, status, viewer: orgAdminViewer });

        renderWithQueryClient(<CalismaDetayPage />);

        await waitFor(() => {
          expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy();
        });
        expect(reportLink()).toBeNull();
      }
    );

    it("bekleyen olmayan durumda (ACTIVE) öğrenci bağlantıyı görmez", async () => {
      vi.mocked(getEngagement).mockResolvedValueOnce(baseEngagement);

      renderWithQueryClient(<CalismaDetayPage />);

      await waitFor(() => {
        expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy();
      });
      expect(reportLink()).toBeNull();
    });
  });
});
