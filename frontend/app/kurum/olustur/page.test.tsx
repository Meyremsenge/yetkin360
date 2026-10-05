import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import KurumOlusturPage from "./page";
import { createInstitution } from "@/lib/api/institutions";
import { ApiError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/institutions", () => ({
  createInstitution: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockPush = vi.fn();
const mockSession = {
  data: { user: { id: "user-1", email: "test@test.com" }, organizations: [], institutions: [], talent_profile: null },
  error: null,
  isPending: false,
  isError: false,
  refetch: vi.fn(),
};

describe("KurumOlusturPage (/kurum/olustur)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
    vi.mocked(useSession).mockReturnValue(mockSession as unknown as ReturnType<typeof useSession>);
  });

  afterEach(() => {
    cleanup();
  });

  it("form render edilir — sadece ad alanı var", () => {
    renderWithQueryClient(<KurumOlusturPage />);

    expect(screen.getByLabelText("Ad")).toBeTruthy();
    expect(screen.queryByLabelText(/[Dd]omain|[Aa]lan [Aa]dı/)).toBeNull();
  });

  it("happy path: ad girilip gönderilince createInstitution çağrılır, panele yönlendirilir", async () => {
    vi.mocked(createInstitution).mockResolvedValueOnce({
      id: "inst-1", name: "Test Üniversitesi", domain: null, verification_level: "T1", status: "ACTIVE",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<KurumOlusturPage />);

    await user.type(screen.getByLabelText("Ad"), "Test Üniversitesi");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(createInstitution).toHaveBeenCalledWith("Test Üniversitesi");
      expect(mockPush).toHaveBeenCalledWith("/kurum/inst-1/panel");
    });
  });

  it("hata durumunda jenerik mesaj gösterilir, yönlendirme olmaz", async () => {
    vi.mocked(createInstitution).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<KurumOlusturPage />);

    await user.type(screen.getByLabelText("Ad"), "x");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(screen.getByText("İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin.")).toBeTruthy();
    });
    expect(mockPush).not.toHaveBeenCalled();
  });
});
