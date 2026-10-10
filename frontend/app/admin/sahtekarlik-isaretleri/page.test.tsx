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


function paged<T>(items: T[], extra: Partial<{ limit: number; offset: number; has_more: boolean }> = {}) {
  return { items, limit: 50, offset: 0, has_more: false, ...extra };
}

const mockFlag = {
  id: "flag-1",
  subject_type: "ATTESTATION" as const,
  subject_id: "att-12345678-abcd",
  subject_label: null,
  signal: null,
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
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(paged([]));

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
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(paged([mockFlag]));

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("Şablon ifade paterni tespit edildi.")).toBeTruthy();
    });
    expect(screen.getByText("Yüksek")).toBeTruthy();
    expect(screen.getByText("anthropic/claude-haiku-4.5")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Sahtekarlık Onayla/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Yanlış Alarm/ })).toBeTruthy();
  });

  it("kuruluş işareti — kuruluş adı, sinyal etiketi ve 'Kural' kaynağı gösterilir", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(
      paged([
        {
          ...mockFlag,
          id: "flag-org",
          subject_type: "ORGANIZATION" as const,
          subject_id: "org-12345678-abcd",
          subject_label: "Şüpheli Kuruluş Ltd.",
          signal: "NEW_ORG_BURST",
          reason: "Kuruluş 7 günden yeni ve şimdiden 3 çalışmasına tanıklık verilmiş.",
          model: "rules-v1",
        },
      ])
    );

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText(/Şüpheli Kuruluş Ltd\./)).toBeTruthy();
    });
    expect(screen.getByText(/^Kuruluş:/)).toBeTruthy();
    expect(screen.getByText("Yeni kuruluşta ani tanıklık artışı")).toBeTruthy();
    expect(screen.getByText("Kural")).toBeTruthy();
  });

  it("tanıklık işareti — ad yoksa kısa kimlik ve 'Yapay zeka' kaynağı gösterilir", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(paged([mockFlag]));

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText(/Tanıklık: #att-1234/)).toBeTruthy();
    });
    expect(screen.getByText("Yapay zeka")).toBeTruthy();
  });

  it("bilinmeyen sinyal kodu ham haliyle gösterilir (ekran kırılmaz)", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(
      paged([{ ...mockFlag, signal: "FUTURE_SIGNAL", model: "rules-v1" }])
    );

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("FUTURE_SIGNAL")).toBeTruthy();
    });
  });

  it("Sahtekarlık Onayla tıklanınca resolveFraudFlag CONFIRMED ile çağrılır ve satır kaybolur", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(paged([mockFlag]));
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
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(paged([mockFlag]));
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
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce(paged([mockFlag]));
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


/**
 * admin-sayfalama-ve-kabuk — AC-1/AC-8/AC-9: Önceki/Sonraki sayfalama + hata/tekrar dene.
 */
describe("SahtekarlikIsaretleriPage — sayfalama", () => {
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

  it("has_more=true ise Sonraki etkin; tıklanınca offset=50 ile istek atılır", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    vi.mocked(adminApi.getFraudQueue)
      .mockResolvedValueOnce({ items: [mockFlag], limit: 50, offset: 0, has_more: true })
      .mockResolvedValueOnce({ items: [], limit: 50, offset: 50, has_more: false });

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    const next = await screen.findByRole("button", { name: "Sonraki" });
    expect((next as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Önceki" }) as HTMLButtonElement).disabled).toBe(true);

    await userEvent.setup().click(next);

    await waitFor(() => {
      expect(adminApi.getFraudQueue).toHaveBeenLastCalledWith({ limit: 50, offset: 50 });
    });
  });

  it("has_more=false ve offset=0 iken sayfalama gösterilmez", async () => {
    vi.mocked(adminApi.getFraudQueue).mockResolvedValueOnce({
      items: [mockFlag],
      limit: 50,
      offset: 0,
      has_more: false,
    });

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    await waitFor(() => {
      expect(screen.getByText("Şablon ifade paterni tespit edildi.")).toBeTruthy();
    });
    expect(screen.queryByRole("navigation", { name: "Sayfalama" })).toBeNull();
  });

  it("liste hatasında aria-live uyarısı ve 'Tekrar dene' görünür; tıklanınca yeniden istenir", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    vi.mocked(adminApi.getFraudQueue)
      .mockRejectedValueOnce(new ApiError({ status: 500, code: "INTERNAL_ERROR", message: "x", requestId: null }))
      .mockResolvedValueOnce({ items: [mockFlag], limit: 50, offset: 0, has_more: false });

    renderWithQueryClient(<SahtekarlikIsaretleriPage />);

    const retry = await screen.findByRole("button", { name: "Tekrar dene" });
    expect(screen.getByRole("alert")).toBeTruthy();

    await userEvent.setup().click(retry);

    await waitFor(() => {
      expect(screen.getByText("Şablon ifade paterni tespit edildi.")).toBeTruthy();
    });
  });
});
