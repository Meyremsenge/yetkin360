import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CalismaDetayPage from "@/app/calismalar/[id]/page";
import { useSession } from "@/lib/session/use-session";
import { useParams } from "next/navigation";
import { getEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";

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
  tasks: [{ id: "task-1", title: "API şeması", status: "DONE" }],
  deliverables: [],
};

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
    vi.mocked(getEngagement).mockResolvedValueOnce(baseEngagement);

    const { container } = renderWithQueryClient(<CalismaDetayPage />);

    await waitFor(() => {
      expect(screen.getByText("Yaz Kısa Projesi")).toBeTruthy();
      expect(screen.getByText("Aktif")).toBeTruthy();
      expect(container.textContent).toContain("API şeması");
      expect(container.textContent).toContain("DONE");
      expect(screen.getByText("Henüz çıktı yüklenmemiş.")).toBeTruthy();
      // ACTIVE durumundan aday geçişler: CANCELLED, PENDING_EVALUATION
      expect(screen.getByText("İptal Et")).toBeTruthy();
      expect(screen.getByText("Değerlendirmeye Gönder")).toBeTruthy();
    });
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
});
