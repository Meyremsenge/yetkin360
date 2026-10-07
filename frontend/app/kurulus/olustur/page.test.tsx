import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import KurulusOlusturPage from "./page";
import { createOrganization } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/organizations", () => ({
  createOrganization: vi.fn(),
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

describe("KurulusOlusturPage (/kurulus/olustur)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
    vi.mocked(useSession).mockReturnValue(mockSession as unknown as ReturnType<typeof useSession>);
  });

  afterEach(() => {
    cleanup();
  });

  it("form render edilir — ad zorunlu, domain/legal_id opsiyonel", () => {
    renderWithQueryClient(<KurulusOlusturPage />);

    expect(screen.getByLabelText("Ad")).toBeTruthy();
    expect(screen.getByLabelText("Alan Adı (opsiyonel)")).toBeTruthy();
    expect(screen.getByLabelText("Ticari Sicil No (opsiyonel)")).toBeTruthy();
  });

  it("happy path: doldurulup gönderilince createOrganization çağrılır, panele yönlendirilir", async () => {
    vi.mocked(createOrganization).mockResolvedValueOnce({
      id: "org-1", name: "Acme A.Ş.", domain: "acme.com", legal_id: null,
      verification_level: "T1", status: "ACTIVE",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<KurulusOlusturPage />);

    await user.type(screen.getByLabelText("Ad"), "Acme A.Ş.");
    await user.type(screen.getByLabelText("Alan Adı (opsiyonel)"), "acme.com");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(createOrganization).toHaveBeenCalledWith({ name: "Acme A.Ş.", domain: "acme.com", legal_id: undefined });
      expect(mockPush).toHaveBeenCalledWith("/kurulus/org-1/panel");
    });
  });

  it("domain/legal_id boşsa undefined olarak gönderilir", async () => {
    vi.mocked(createOrganization).mockResolvedValueOnce({
      id: "org-2", name: "Küçük Org", domain: null, legal_id: null, verification_level: "T1", status: "ACTIVE",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<KurulusOlusturPage />);

    await user.type(screen.getByLabelText("Ad"), "Küçük Org");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(createOrganization).toHaveBeenCalledWith({ name: "Küçük Org", domain: undefined, legal_id: undefined });
    });
  });

  it("409 LEGAL_ID_TAKEN → ilgili hata mesajı gösterilir, yönlendirme olmaz", async () => {
    vi.mocked(createOrganization).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "LEGAL_ID_TAKEN", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<KurulusOlusturPage />);

    await user.type(screen.getByLabelText("Ad"), "x");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(screen.getByText("Bu ticari sicil numarası zaten kayıtlı.")).toBeTruthy();
    });
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("422 VALIDATION_ERROR → doğrulama hatası mesajı gösterilir", async () => {
    vi.mocked(createOrganization).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<KurulusOlusturPage />);

    await user.type(screen.getByLabelText("Ad"), "x");
    await user.click(screen.getByText("Oluştur"));

    await waitFor(() => {
      expect(screen.getByText("Ad veya alan adı geçersiz. Lütfen kontrol edin.")).toBeTruthy();
    });
  });
});
