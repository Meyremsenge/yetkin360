import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KurumBaglanPage from "./page";
import { useParams } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import { requestInstitutionLink } from "@/lib/api/institutions";
import { ApiError, NetworkError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("@/lib/session/use-session");

vi.mock("@/lib/api/institutions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/institutions")>();
  return {
    ...actual,
    requestInstitutionLink: vi.fn(),
  };
});

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockSession = {
  data: {
    user: { id: "user-1", email: "talent@test.com" },
    organizations: [],
    institutions: [],
    talent_profile: { headline: null },
  },
  error: null,
  isPending: false,
  isError: false,
  refetch: vi.fn(),
};

/**
 * YET-197/IS-10: /kurum/{id}/baglan — kurumun paylaştığı linkle bağlanma talebi.
 */
describe("KurumBaglanPage (/kurum/[id]/baglan)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "inst-1" });
    vi.mocked(useSession).mockReturnValue(mockSession as unknown as ReturnType<typeof useSession>);
  });

  afterEach(() => {
    cleanup();
  });

  it("happy path: talep gönderilince başarı mesajı ve profile dönüş linki gösterilir", async () => {
    const user = userEvent.setup();
    vi.mocked(requestInstitutionLink).mockResolvedValueOnce(undefined);

    renderWithQueryClient(<KurumBaglanPage />);

    await user.click(screen.getByText("Talep Gönder"));

    await waitFor(() => {
      expect(requestInstitutionLink).toHaveBeenCalledWith("inst-1");
      expect(screen.getByText(/Bağlanma talebiniz gönderildi/i)).toBeTruthy();
      expect(screen.getByText("Profiline dön")).toBeTruthy();
    });
  });

  it("409 - zaten bekleyen talep varsa uygun hata mesajı gösterilir", async () => {
    const user = userEvent.setup();
    vi.mocked(requestInstitutionLink).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "HTTP_ERROR", message: "x", requestId: null })
    );

    renderWithQueryClient(<KurumBaglanPage />);

    await user.click(screen.getByText("Talep Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Bu kuruma zaten bekleyen bir talebiniz var.")).toBeTruthy();
    });
  });

  it("404 - kurum bulunamazsa uygun hata mesajı gösterilir", async () => {
    const user = userEvent.setup();
    vi.mocked(requestInstitutionLink).mockRejectedValueOnce(
      new ApiError({ status: 404, code: "HTTP_ERROR", message: "x", requestId: null })
    );

    renderWithQueryClient(<KurumBaglanPage />);

    await user.click(screen.getByText("Talep Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Kurum bulunamadı.")).toBeTruthy();
    });
  });

  it("network error - jenerik mesaj yerine ağ hatası mesajı gösterilir", async () => {
    const user = userEvent.setup();
    vi.mocked(requestInstitutionLink).mockRejectedValueOnce(new NetworkError("network"));

    renderWithQueryClient(<KurumBaglanPage />);

    await user.click(screen.getByText("Talep Gönder"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });
});
