import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SahtekarlikIsaretleriPage from "@/app/admin/sahtekarlik-isaretleri/page";
import { useSession } from "@/lib/session/use-session";
import { ApiError } from "@/lib/api/errors";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/admin");

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockFlag = {
  id: "flag-1",
  subject_type: "ATTESTATION",
  subject_id: "att-12345678-abcd",
  reason: "Şablon ifade paterni tespit edildi.",
  confidence: "HIGH" as const,
  model: "anthropic/claude-haiku-4.5",
  created_at: "2026-10-10T10:00:00Z",
};

/**
 * PLAN 3.54 — Admin fraud-queue ekranı testi.
 */
describe("SahtekarlikIsaretleriPage (/admin/sahtekarlik-isaretleri)", () => {
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

  it("yüklenirken 'Yükleniyor...' gösterir", () => {
    vi.mocked(adminApi.getFraudQueue).mockReturnValue(new Promise(() => {}));

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    expect(screen.getByText("Yükleniyor...")).toBeTruthy();
  });

  it("kuyruk boşsa boş durum mesajı gösterir", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce({ items: [] });

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("Bekleyen işaret yok")).toBeTruthy();
    });
  });

  it("hata durumunda jenerik hata mesajı gösterir", async () => {
    vi.mocked(adminApi.getFraudQueue).mockRejectedValueOnce(new Error("boom"));

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });

  it("dolu kuyruk — reason, confidence, model ve onay/reddet butonları gösterilir", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce({ items: [mockFlag] });

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("Şablon ifade paterni tespit edildi.")).toBeTruthy();
    });
    expect(screen.getByText("Yüksek")).toBeTruthy();
    expect(screen.getByText("anthropic/claude-haiku-4.5")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Sahtekarlık Onayla/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Yanlış Alarm/ })).toBeTruthy();
  });

  it("Sahtekarlık Onayla tıklanınca resolveFraudFlag CONFIRMED ile çağrılır ve satır kaybolur", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce({ items: [mockFlag] });
    vi.mocked(adminApi.resolveFraudFlag).mockResolvedValueOnce({ ...mockFlag });

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("Şablon ifade paterni tespit edildi.")).toBeTruthy();
    });

    screen.getByRole("button", { name: /Sahtekarlık Onayla/ }).click();

    await waitFor(() => {
      expect(adminApi.resolveFraudFlag).toHaveBeenCalledWith("flag-1", "CONFIRMED");
    });
    await waitFor(() => {
      expect(screen.queryByText("Şablon ifade paterni tespit edildi.")).toBeNull();
    });
  });

  it("Yanlış Alarm tıklanınca resolveFraudFlag DISMISSED ile çağrılır", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce({ items: [mockFlag] });
    vi.mocked(adminApi.resolveFraudFlag).mockResolvedValueOnce({ ...mockFlag });

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("Şablon ifade paterni tespit edildi.")).toBeTruthy();
    });

    screen.getByRole("button", { name: /Yanlış Alarm/ }).click();

    await waitFor(() => {
      expect(adminApi.resolveFraudFlag).toHaveBeenCalledWith("flag-1", "DISMISSED");
    });
  });

  it("409 NOT_PENDING hatasında uyarı mesajı gösterir", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce({ items: [mockFlag] });
    vi.mocked(adminApi.resolveFraudFlag).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "NOT_PENDING", message: "x", requestId: null })
    );

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("Şablon ifade paterni tespit edildi.")).toBeTruthy();
    });

    screen.getByRole("button", { name: /Sahtekarlık Onayla/ }).click();

    await waitFor(() => {
      expect(screen.getByText("Bu işaret zaten incelenmiş.")).toBeTruthy();
    });
  });
});
