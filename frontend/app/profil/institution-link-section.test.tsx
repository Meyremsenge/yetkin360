import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import InstitutionLinkSection from "./institution-link-section";
import { useSession } from "@/lib/session/use-session";
import { listMyLinkRequests } from "@/lib/api/institutions";

vi.mock("@/lib/session/use-session");

vi.mock("@/lib/api/institutions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/institutions")>();
  return {
    ...actual,
    listMyLinkRequests: vi.fn(),
  };
});

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function mockSessionWith(institutions: Array<{ id: string; name: string }>) {
  vi.mocked(useSession).mockReturnValue({
    data: {
      user: { id: "user-1", email: "talent@test.com" },
      organizations: [],
      institutions,
      talent_profile: { headline: null },
    },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>);
}

/**
 * YET-197/IS-10: Profil sayfasındaki kurum bağlantısı + talep geçmişi bölümü.
 */
describe("InstitutionLinkSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("bağlı değilse 'henüz bağlı değilsiniz' mesajı ve ipucu gösterilir (form/arama YOK)", async () => {
    mockSessionWith([]);
    vi.mocked(listMyLinkRequests).mockResolvedValueOnce({ items: [] });

    renderWithQueryClient(<InstitutionLinkSection />);

    await waitFor(() => {
      expect(screen.getByText("Henüz bir kuruma bağlı değilsiniz.")).toBeTruthy();
      expect(screen.getByText(/bağlantıyı kullanarak/i)).toBeTruthy();
    });
  });

  it("bağlıysa kurum adı gösterilir", async () => {
    mockSessionWith([{ id: "inst-1", name: "Test Üniversitesi" }]);
    vi.mocked(listMyLinkRequests).mockResolvedValueOnce({ items: [] });

    renderWithQueryClient(<InstitutionLinkSection />);

    await waitFor(() => {
      expect(screen.getByText("Test Üniversitesi")).toBeTruthy();
    });
  });

  it("kendi talep geçmişi listelenir ve statü rozetleri doğru gösterilir", async () => {
    mockSessionWith([]);
    vi.mocked(listMyLinkRequests).mockResolvedValueOnce({
      items: [
        { id: "r1", institution_id: "i1", institution_name: "A Üniversitesi", status: "PENDING", requested_at: "2026-10-01T00:00:00Z", decided_at: null },
        { id: "r2", institution_id: "i2", institution_name: "B Üniversitesi", status: "REJECTED", requested_at: "2026-09-01T00:00:00Z", decided_at: "2026-09-02T00:00:00Z" },
      ],
    });

    renderWithQueryClient(<InstitutionLinkSection />);

    await waitFor(() => {
      expect(screen.getByText("A Üniversitesi")).toBeTruthy();
      expect(screen.getByText("Onay Bekliyor")).toBeTruthy();
      expect(screen.getByText("B Üniversitesi")).toBeTruthy();
      expect(screen.getByText("Reddedildi")).toBeTruthy();
    });
  });

  it("hiç talep yoksa empty-state mesajı gösterilir", async () => {
    mockSessionWith([]);
    vi.mocked(listMyLinkRequests).mockResolvedValueOnce({ items: [] });

    renderWithQueryClient(<InstitutionLinkSection />);

    await waitFor(() => {
      expect(screen.getByText("Henüz bir bağlanma talebiniz yok.")).toBeTruthy();
    });
  });

  it("geçmiş yüklenemezse hata mesajı ve tekrar dene butonu gösterilir", async () => {
    mockSessionWith([]);
    vi.mocked(listMyLinkRequests).mockRejectedValueOnce(new Error("boom"));

    renderWithQueryClient(<InstitutionLinkSection />);

    await waitFor(() => {
      expect(screen.getByText("Bağlanma talepleriniz yüklenemedi.")).toBeTruthy();
      expect(screen.getByText("Tekrar dene")).toBeTruthy();
    });
  });
});
