import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KurulusSecPage from "@/app/calismalar/kurulus-sec/page";
import { listApprovers, listOrganizationDirectory } from "@/lib/api/organizations";
import { useSession } from "@/lib/session/use-session";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/organizations", () => ({
  listOrganizationDirectory: vi.fn(),
  listApprovers: vi.fn(),
}));
vi.mock("@/lib/session/use-session");

function mockAuthenticatedSession() {
  vi.mocked(useSession).mockReturnValue({
    data: {
      user: { id: "user-1", email: "user@test.com" },
      organizations: [],
      institutions: [],
      talent_profile: null,
    },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>);
}

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

/**
 * PLAN 3.53: öğrenci tüm kuruluşlardan serbestçe arayıp seçebilsin ekranı.
 */
describe("KurulusSecPage (/calismalar/kurulus-sec)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthenticatedSession();
  });

  afterEach(() => {
    cleanup();
  });

  it("yüklenirken yükleme durumu gösterir", async () => {
    vi.mocked(listOrganizationDirectory).mockReturnValue(new Promise(() => {}));

    renderWithQueryClient(<KurulusSecPage />);

    expect(screen.getByRole("status")).toBeTruthy();
  });

  it("hata verirse hata mesajı ve tekrar dene butonu gösterir", async () => {
    vi.mocked(listOrganizationDirectory).mockRejectedValueOnce(new Error("network fail"));

    renderWithQueryClient(<KurulusSecPage />);

    await waitFor(() => {
      expect(screen.getByText("Kuruluşlar yüklenemedi.")).toBeTruthy();
    });
  });

  it("liste boşsa boş durum mesajı gösterir", async () => {
    vi.mocked(listOrganizationDirectory).mockResolvedValueOnce([]);

    renderWithQueryClient(<KurulusSecPage />);

    await waitFor(() => {
      expect(screen.getByText("Aramanızla eşleşen bir kuruluş bulunamadı.")).toBeTruthy();
    });
  });

  it("dönen kuruluşları ad, domain ve doğrulama seviyesiyle listeler", async () => {
    vi.mocked(listOrganizationDirectory).mockResolvedValueOnce([
      { id: "org-1", name: "Acme A.Ş.", domain: "acme.com", verification_level: "T2" },
      { id: "org-2", name: "Küçük Kuruluş", domain: null, verification_level: "T1" },
    ]);

    renderWithQueryClient(<KurulusSecPage />);

    await waitFor(() => {
      expect(screen.getByText("Acme A.Ş.")).toBeTruthy();
    });

    expect(screen.getByText("acme.com")).toBeTruthy();
    expect(screen.getByText("Alan adı doğrulandı")).toBeTruthy();
    expect(screen.getByText("Küçük Kuruluş")).toBeTruthy();
    expect(screen.getByText("Temel doğrulama")).toBeTruthy();
    expect(screen.getByText("2 kuruluş")).toBeTruthy();
    // Nothing is fetched or offered before a card is chosen.
    expect(listApprovers).not.toHaveBeenCalled();
    expect(screen.queryByRole("link", { name: /Bu kuruluşla devam et/ })).toBeNull();
  });

  it("kuruluş seçilince onaylayıcıları maskeli e-postayla gösterir ve olustur linkine yönlendirir", async () => {
    vi.mocked(listOrganizationDirectory).mockResolvedValueOnce([
      { id: "org-1", name: "Acme A.Ş.", domain: "acme.com", verification_level: "T2" },
    ]);
    vi.mocked(listApprovers).mockResolvedValueOnce([
      { user_id: "u-1", display_name: "Mehmet Kaya", unit: "Yazılım", email_hint: "me•••@acme.com" },
    ]);

    renderWithQueryClient(<KurulusSecPage />);

    const card = await screen.findByRole("button", { name: /Acme A\.Ş\./ });
    expect(card.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(card);

    expect(await screen.findByText("Mehmet Kaya")).toBeTruthy();
    expect(screen.getByText("me•••@acme.com")).toBeTruthy();
    expect(listApprovers).toHaveBeenCalledWith("org-1");
    expect(card.getAttribute("aria-expanded")).toBe("true");
    const link = screen.getByRole("link", { name: /Bu kuruluşla devam et/ });
    expect(link.getAttribute("href")).toBe("/calismalar/olustur?organization_id=org-1");
  });

  it("onaylayıcı yoksa kuruluş yöneticisine gideceğini söyler, devam yine mümkündür", async () => {
    vi.mocked(listOrganizationDirectory).mockResolvedValueOnce([
      { id: "org-1", name: "Acme A.Ş.", domain: "acme.com", verification_level: "T2" },
    ]);
    vi.mocked(listApprovers).mockResolvedValueOnce([]);

    renderWithQueryClient(<KurulusSecPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Acme A\.Ş\./ }));

    expect(await screen.findByText(messages.kurulusSec.approversEmpty)).toBeTruthy();
    expect(screen.getByRole("link", { name: /Bu kuruluşla devam et/ })).toBeTruthy();
  });

  it("arama kutusuna yazıldığında listOrganizationDirectory arama terimiyle çağrılır", async () => {
    vi.mocked(listOrganizationDirectory).mockResolvedValue([]);

    renderWithQueryClient(<KurulusSecPage />);

    await waitFor(() => {
      expect(listOrganizationDirectory).toHaveBeenCalledWith("");
    });

    const input = screen.getByPlaceholderText("Kuruluş adı ara...");
    fireEvent.change(input, { target: { value: "Acme" } });

    await waitFor(() => {
      expect(listOrganizationDirectory).toHaveBeenCalledWith("Acme");
    });
  });
});
