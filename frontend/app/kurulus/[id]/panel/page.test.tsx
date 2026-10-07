import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KurulusPanelPage from "./page";
import { useParams } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import { getOrganization, inviteOrgMember, verifyDomain } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("@/lib/session/use-session");

vi.mock("@/lib/api/organizations", () => ({
  getOrganization: vi.fn(),
  inviteOrgMember: vi.fn(),
  verifyDomain: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockSession = {
  data: { user: { id: "user-1", email: "admin@test.com" }, organizations: [{ id: "org-1", name: "Acme" }], institutions: [], talent_profile: null },
  error: null,
  isPending: false,
  isError: false,
  refetch: vi.fn(),
};

const baseOrg = {
  id: "org-1",
  name: "Acme A.Ş.",
  domain: "acme.com",
  legal_id: "ORG-1",
  verification_level: "T1",
  status: "ACTIVE",
};

describe("KurulusPanelPage (/kurulus/[id]/panel)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "org-1" });
    vi.mocked(useSession).mockReturnValue(mockSession as unknown as ReturnType<typeof useSession>);
  });

  afterEach(() => {
    cleanup();
  });

  it("happy path - organizasyon adı ve sicil no render edilir", async () => {
    vi.mocked(getOrganization).mockResolvedValueOnce(baseOrg);

    renderWithQueryClient(<KurulusPanelPage />);

    await waitFor(() => {
      expect(screen.getByText("Acme A.Ş.")).toBeTruthy();
      expect(screen.getByText("Ticari Sicil No: ORG-1")).toBeTruthy();
    });
  });

  it("404 - jenerik hata mesajı gösterilir", async () => {
    vi.mocked(getOrganization).mockRejectedValueOnce(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "Organizasyon bulunamadı.", requestId: null })
    );

    renderWithQueryClient(<KurulusPanelPage />);

    await waitFor(() => {
      expect(screen.getByText(/Organizasyon bulunamadı/i)).toBeTruthy();
    });
  });

  describe("Alan adı doğrulama bölümü", () => {
    it("domain yoksa doğrulama yapılamaz mesajı gösterilir, buton yok", async () => {
      vi.mocked(getOrganization).mockResolvedValueOnce({ ...baseOrg, domain: null });

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => {
        expect(screen.getByText("Bu organizasyon için alan adı belirlenmemiş, doğrulama yapılamaz.")).toBeTruthy();
      });
      expect(screen.queryByText("Doğrulamayı Kontrol Et")).toBeNull();
    });

    it("domain T1'de ise Doğrulamayı Kontrol Et butonu gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValueOnce(baseOrg); // T1

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => {
        expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy();
      });
    });

    it("domain T2+ ise doğrulanmış rozeti gösterilir, buton yok", async () => {
      vi.mocked(getOrganization).mockResolvedValueOnce({ ...baseOrg, verification_level: "T2" });

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => {
        expect(screen.getByText(/Doğrulanmış alan adı/)).toBeTruthy();
      });
      expect(screen.queryByText("Doğrulamayı Kontrol Et")).toBeNull();
    });

    it("kontrol edince pending dönerse TXT kaydı + pending mesajı gösterilir, buton Tekrar Dene'ye döner", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockResolvedValueOnce({ dns_txt_record: "yetkin360_verify_abc123", status: "pending" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(verifyDomain).toHaveBeenCalledWith("org-1");
        expect(screen.getByText("yetkin360_verify_abc123")).toBeTruthy();
        expect(screen.getByText(/Kayıt henüz bulunamadı/)).toBeTruthy();
        expect(screen.getByText("Tekrar Dene")).toBeTruthy();
      });
    });

    it("kontrol edince verified dönerse başarı mesajı gösterilir ve organizasyon yeniden çekilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockResolvedValueOnce({ dns_txt_record: "yetkin360_verify_abc123", status: "verified" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(screen.getByText("Alan adı doğrulandı.")).toBeTruthy();
      });
      // invalidateQueries sonrası getOrganization tekrar çağrılır (mount + invalidate)
      await waitFor(() => {
        expect(vi.mocked(getOrganization)).toHaveBeenCalledTimes(2);
      });
    });

    it("400 FREE_EMAIL_DOMAIN → ilgili hata mesajı gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockRejectedValueOnce(
        new ApiError({ status: 400, code: "FREE_EMAIL_DOMAIN", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(screen.getByText(/Ücretsiz e-posta sağlayıcıları/)).toBeTruthy();
      });
    });

    it("429 TOO_MANY_REQUESTS → rate limit mesajı gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockRejectedValueOnce(
        new ApiError({ status: 429, code: "TOO_MANY_REQUESTS", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(screen.getByText(/Çok sık deniyorsunuz/)).toBeTruthy();
      });
    });

    it("409 DOMAIN_ALREADY_VERIFIED → ilgili hata mesajı gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockRejectedValueOnce(
        new ApiError({ status: 409, code: "DOMAIN_ALREADY_VERIFIED", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(screen.getByText(/başka bir organizasyonda zaten doğrulanmış/)).toBeTruthy();
      });
    });
  });

  describe("Üye davet bölümü", () => {
    it("happy path: doldurulup gönderilince inviteOrgMember çağrılır, başarı mesajı gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(inviteOrgMember).mockResolvedValueOnce({ status: "queued" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByLabelText("E-posta")).toBeTruthy());
      await user.type(screen.getByLabelText("E-posta"), "yeni-uye@test.com");
      await user.click(screen.getByText("Davet Gönder"));

      await waitFor(() => {
        expect(inviteOrgMember).toHaveBeenCalledWith("org-1", "yeni-uye@test.com", "MEMBER");
        expect(screen.getByText("Davet kuyruğa alındı.")).toBeTruthy();
      });
    });

    it("rol ADMIN seçilirse doğru rolle çağrılır", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(inviteOrgMember).mockResolvedValueOnce({ status: "queued" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByLabelText("E-posta")).toBeTruthy());
      await user.type(screen.getByLabelText("E-posta"), "yeni-admin@test.com");
      await user.selectOptions(screen.getByLabelText("Rol"), "ADMIN");
      await user.click(screen.getByText("Davet Gönder"));

      await waitFor(() => {
        expect(inviteOrgMember).toHaveBeenCalledWith("org-1", "yeni-admin@test.com", "ADMIN");
      });
    });

    it("davet başarısız olursa hata mesajı gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(inviteOrgMember).mockRejectedValueOnce(
        new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByLabelText("E-posta")).toBeTruthy());
      await user.type(screen.getByLabelText("E-posta"), "x@test.com");
      await user.click(screen.getByText("Davet Gönder"));

      await waitFor(() => {
        expect(screen.getByText("Davet gönderilemedi.")).toBeTruthy();
      });
    });
  });
});
