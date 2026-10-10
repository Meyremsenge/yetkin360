import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { AppShell } from "@/components/app-shell";
import { useSession, useLogout } from "@/lib/session/use-session";
import {
  NetworkError,
  ApiError,
  SessionExpiredError,
  InvalidResponseError,
} from "@/lib/api/errors";
import messages from "@/messages/tr.json";

vi.mock("@/lib/session/use-session");

/**
 * AC-1: Yüklenme iskeleti (aria-busy).
 * AC-5: Ağ hatası + cache varsa children + alert; yoksa hata sayfası.
 * AC-7: InvalidResponseError → hata ekranı.
 * AC-8: Logout → başarılı veya başarısız + alert.
 * AC-12: organizations boşsa boş durum (hata değil).
 * AC-S1: SessionExpiredError → children render EDİLMEZ, kullanıcı verisi yok.
 */

describe("AppShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("AC-1: Loading state — aria-busy", () => {
    it("AC-1: isPending=true iken aria-busy='true'", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: null,
        isPending: true,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      const { container } = render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      const busyElement = container.querySelector('[aria-busy="true"]');
      expect(busyElement).toBeTruthy();
    });

    it("AC-1: isPending=true iken 'Yükleniyor...' metni görünür", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: null,
        isPending: true,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(screen.getByText(messages.shell.loading)).toBeTruthy();
    });

    it("AC-1: isPending=true iken children RENDER EDİLMEZ", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: null,
        isPending: true,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Bu metin görünmemeli</p>
        </AppShell>
      );

      expect(screen.queryByText("Bu metin görünmemeli")).toBeNull();
    });
  });

  describe("AC-1: Happy path — data ve children render", () => {
    it("AC-1: data varsa children render edilir", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [{ id: "org-1", name: "Test Org" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Ana içerik</p>
        </AppShell>
      );

      expect(screen.getByText("Ana içerik")).toBeTruthy();
    });
  });

  describe("YET-196: e-posta doğrulama bandı", () => {
    function mockSession(emailVerified: boolean | undefined) {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1", email_verified: emailVerified },
          organizations: [{ id: "org-1", name: "Test Org" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
    }

    it("email_verified=false iken bant ve yeniden gönder düğmesi görünür", () => {
      mockSession(false);
      render(<AppShell><p>İçerik</p></AppShell>);

      expect(screen.getByText(messages.emailVerificationBanner.message)).toBeTruthy();
      expect(screen.getByRole("button", { name: messages.emailVerificationBanner.resend })).toBeTruthy();
      expect(screen.getByText("İçerik")).toBeTruthy();
    });

    it("email_verified=true iken bant yoktur", () => {
      mockSession(true);
      render(<AppShell><p>İçerik</p></AppShell>);

      expect(screen.queryByText(messages.emailVerificationBanner.message)).toBeNull();
    });

    it("alan yoksa (eski yanıt) bant gösterilmez", () => {
      mockSession(undefined);
      render(<AppShell><p>İçerik</p></AppShell>);

      expect(screen.queryByText(messages.emailVerificationBanner.message)).toBeNull();
    });
  });

  describe("AC-12: organizations boş durum (hata değil)", () => {
    it("AC-12: organizations=[] boşsa 'Henüz bir kuruluşunuz yok' gösterilir", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(
        screen.getByText(messages.shell.noOrganizations)
      ).toBeTruthy();
      // Oturum geçerli olduğu için children render edilir
      expect(screen.getByText("İçerik")).toBeTruthy();
    });

    it("AC-12: boş durum da hata bandı YOKTUR (error !== null)", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(screen.queryByRole("alert")).toBeNull();
    });

    it("AC-12: öğrenci profili varsa kuruluş yok şeridi gösterilmez", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          talent_profile: { public_slug: null },
          organizations: [],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(screen.queryByText(messages.shell.noOrganizations)).toBeNull();
      expect(screen.getByText("İçerik")).toBeTruthy();
    });
  });

  describe("AC-5: Ağ hatası + cache", () => {
    it("AC-5: NetworkError + data varsa children + ErrorBanner", async () => {
      const mockRefetch = vi.fn();
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: new NetworkError("network"),
        isPending: false,
        isError: true,
        refetch: mockRefetch,
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Eski veriler</p>
        </AppShell>
      );

      // Children render edilir (cache varsa)
      expect(screen.getByText("Eski veriler")).toBeTruthy();

      // Hata bandı görünür
      const alert = screen.getByRole("alert");
      expect(alert).toBeTruthy();
      expect(screen.getByText(messages.errors.network)).toBeTruthy();
    });

    it("AC-5: NetworkError + data yoksa ErrorBanner, children YOKTUR", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: new NetworkError("network"),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Bu metin görünmemeli</p>
        </AppShell>
      );

      // Boş beyaz sayfa değil, hata gösterilir
      expect(screen.getByRole("alert")).toBeTruthy();
      expect(screen.queryByText("Bu metin görünmemeli")).toBeNull();
    });

    it("AC-5: NetworkError + retry butonu refetch'i çağırır", () => {
      const mockRefetch = vi.fn();
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: new NetworkError("network"),
        isPending: false,
        isError: true,
        refetch: mockRefetch,
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      const retryButton = screen.getByRole("button", {
        name: messages.errors.retry,
      });
      fireEvent.click(retryButton);

      expect(mockRefetch).toHaveBeenCalled();
    });

    it("AC-5: NetworkError 'timeout' → timeout mesajı", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: new NetworkError("timeout"),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(
        screen.getByText(messages.errors.timeout)
      ).toBeTruthy();
    });
  });

  describe("AC-5: ApiError 5xx — cache korunur", () => {
    it("AC-5: ApiError 500 + data varsa children + alert + requestId", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: new ApiError({
          status: 500,
          code: "INTERNAL_SERVER_ERROR",
          message: "Sunucu hatası",
          requestId: "req-5xx-error",
        }),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Veriler</p>
        </AppShell>
      );

      expect(screen.getByText("Veriler")).toBeTruthy();
      expect(screen.getByRole("alert")).toBeTruthy();
      expect(screen.getByText(/req-5xx-error/)).toBeTruthy();
    });
  });

  describe("AC-7: InvalidResponseError", () => {
    it("AC-7: InvalidResponseError → 'Bilgileriniz şu an yüklenemedi' + destek kodu", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: new InvalidResponseError("Boş gövde"),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(
        screen.getByText(messages.session.loadFailed)
      ).toBeTruthy();
      expect(screen.getByRole("alert")).toBeTruthy();
    });

    it("AC-7: InvalidResponseError + children RENDER EDİLMEZ", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: new InvalidResponseError("Boş gövde"),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Hiçbir veri gösterilmemeli</p>
        </AppShell>
      );

      expect(
        screen.queryByText("Hiçbir veri gösterilmemeli")
      ).toBeNull();
    });
  });

  describe("AC-S1: SessionExpiredError → children render EDİLMEZ", () => {
    it("AC-S1: SessionExpiredError → children RENDER EDİLMEZ", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-123", email: "user@test.com" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: new SessionExpiredError(),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Kullanıcı verisi gösterilmemeli</p>
        </AppShell>
      );

      expect(
        screen.queryByText("Kullanıcı verisi gösterilmemeli")
      ).toBeNull();
    });

    it("AC-S1: SessionExpiredError → user.email render edilmez", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-123", email: "secret@test.com" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: new SessionExpiredError(),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>Email: {"{user.email}"}</p>
        </AppShell>
      );

      expect(screen.queryByText(/secret@test\.com/)).toBeNull();
    });

    it("AC-S1: SessionExpiredError → hata ekranı gösterilir", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: new SessionExpiredError(),
        isPending: false,
        isError: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });

  describe("AC-8: Logout", () => {
    it("AC-8: logout butonu 'Çıkış' metni içerir", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: false,
      });

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      expect(
        screen.getByRole("button", { name: messages.session.logout })
      ).toBeTruthy();
    });

    it("AC-8: logout butonu tıklanınca logout() çağrılır", async () => {
      const mockLogout = vi.fn();
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: mockLogout,
        isPending: false,
        isError: false,
      });

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      const button = screen.getByRole("button", {
        name: messages.session.logout,
      });
      fireEvent.click(button);

      expect(mockLogout).toHaveBeenCalled();
    });

    it("AC-8: logout isError=true ise 'Çıkış tamamlanamadı' alert gösterilir", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: true,
      });

      render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      const alert = screen.getByRole("alert");
      expect(alert).toBeTruthy();
      expect(
        screen.getByText(messages.session.logoutFailed)
      ).toBeTruthy();
    });

    it("AC-8: logout hata durumunda oturum açık kalır (children görünür)", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: true,
      });

      render(
        <AppShell>
          <p>Oturum açık kaldı</p>
        </AppShell>
      );

      expect(screen.getByText("Oturum açık kaldı")).toBeTruthy();
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });

  describe("YET-245: Admin linkleri rol kontrolü (is_platform_admin)", () => {
    it("AC-1: is_platform_admin=true iken admin linklerini TAM EŞLEŞMEYLE göster", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-admin", is_platform_admin: true },
          organizations: [{ id: "org-1", name: "Test Org" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: false,
      });

      const { container } = render(
        <AppShell>
          <p>Admin İçeriği</p>
        </AppShell>
      );

      // Assert: admin link metinleri TAM EŞLEŞMEYLE bulunur
      const html = container.innerHTML;
      expect(html).toContain(messages.shell.adminVerificationQueueLink);
      expect(html).toContain(messages.shell.adminSkillsLink);
    });

    it("AC-2: is_platform_admin=false iken admin linklerini HİÇ gösterme", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1", is_platform_admin: false },
          organizations: [{ id: "org-1", name: "Test Org" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: false,
      });

      const { container } = render(
        <AppShell>
          <p>Normal Kullanıcı İçeriği</p>
        </AppShell>
      );

      // Assert: admin link metinleri HİÇ bulunmaz
      const html = container.innerHTML;
      expect(html).not.toContain(messages.shell.adminVerificationQueueLink);
      expect(html).not.toContain(messages.shell.adminSkillsLink);

      // Assert: children render edilmiş
      expect(screen.getByText("Normal Kullanıcı İçeriği")).toBeTruthy();
    });

    it("AC-3: isPending=true (loading) iken admin linklerini gösterme", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: undefined,
        error: null,
        isPending: true,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      const { container } = render(
        <AppShell>
          <p>Bu metin loading sırasında görünmemeli</p>
        </AppShell>
      );

      // Assert: admin link metinleri görünmez (loading sırasında fail-closed)
      const html = container.innerHTML;
      expect(html).not.toContain(messages.shell.adminVerificationQueueLink);
      expect(html).not.toContain(messages.shell.adminSkillsLink);

      // Assert: children render edilmemiş
      expect(screen.queryByText("Bu metin loading sırasında görünmemeli")).toBeNull();
    });

    it("AC-4: is_platform_admin=undefined (null/şema hatası) iken admin linklerini gösterme (fail-closed)", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1" }, // is_platform_admin alanı yok (undefined)
          organizations: [{ id: "org-1", name: "Test Org" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: false,
      });

      const { container } = render(
        <AppShell>
          <p>Şema Hatası Durumu</p>
        </AppShell>
      );

      // Assert: admin link metinleri HİÇ bulunmaz (fail-closed, === true kontrolü)
      const html = container.innerHTML;
      expect(html).not.toContain(messages.shell.adminVerificationQueueLink);
      expect(html).not.toContain(messages.shell.adminSkillsLink);

      // Assert: children render edilmiş (veri varsa normal davranış)
      expect(screen.getByText("Şema Hatası Durumu")).toBeTruthy();
    });

    it("AC-5: Çalışmalarım ve Profil linkleri herhangi bir oturum durumunda görünür", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-1", is_platform_admin: false },
          organizations: [],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: false,
      });

      const { container } = render(
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      );

      // Assert: Çalışmalarım ve Profil linkleri TAM EŞLEŞMEYLE bulunur
      const html = container.innerHTML;
      expect(html).toContain(messages.shell.engagementsLink);
      expect(html).toContain(messages.shell.profileLink);

      // Assert: children render edilmiş
      expect(screen.getByText("İçerik")).toBeTruthy();
    });

    it("AC-5: Çalışmalarım ve Profil linkleri admin user'da da görünür", () => {
      vi.mocked(useSession).mockReturnValueOnce({
        data: {
          user: { id: "user-admin", is_platform_admin: true },
          organizations: [{ id: "org-1" }],
          institutions: [],
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValueOnce({
        logout: vi.fn(),
        isPending: false,
        isError: false,
      });

      const { container } = render(
        <AppShell>
          <p>Admin İçeriği</p>
        </AppShell>
      );

      // Assert: Çalışmalarım ve Profil linkleri TAM EŞLEŞMEYLE bulunur
      const html = container.innerHTML;
      expect(html).toContain(messages.shell.engagementsLink);
      expect(html).toContain(messages.shell.profileLink);
    });
  });

  describe("Üst gezinme çubuğu", () => {
    function renderAt(path: string, data: Record<string, unknown>) {
      window.history.pushState({}, "", path);
      vi.mocked(useSession).mockReturnValue({
        data: { organizations: [], institutions: [], ...data },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);
      vi.mocked(useLogout).mockReturnValue({ logout: vi.fn(), isPending: false, isError: false });
      return render(<AppShell><p>İçerik</p></AppShell>);
    }

    afterEach(() => {
      window.history.pushState({}, "", "/");
    });

    it("bulunulan sayfanın menü öğesi aria-current=page alır (alt sayfalar dahil)", () => {
      renderAt("/calismalar/abc/degerlendirme", { user: { id: "u1" }, talent_profile: { public_slug: null } });
      const nav = screen.getByRole("navigation", { name: messages.shell.mainNav });
      const active = within(nav).getByRole("link", { name: messages.shell.engagementsLink });
      expect(active.getAttribute("aria-current")).toBe("page");
      const profile = within(nav).getByRole("link", { name: messages.shell.profileLink });
      expect(profile.getAttribute("aria-current")).toBeNull();
    });

    it("öğrencide bağlam seçici görünmez", () => {
      renderAt("/calismalar", { user: { id: "u1" }, talent_profile: { public_slug: null } });
      expect(screen.queryByRole("button", { name: new RegExp(messages.shell.contextSwitcher) })).toBeNull();
    });

    it("bağlam seçici kuruluş ve kurumları listeler; bulunulan varlığın adını gösterir", () => {
      renderAt("/kurum/inst-1/panel", {
        user: { id: "u1" },
        organizations: [{ id: "org-1", name: "Lale Yazılım A.Ş." }],
        institutions: [{ id: "inst-1", name: "Bilgi Üniversitesi" }],
      });
      const trigger = screen.getByRole("button", { name: new RegExp(messages.shell.contextSwitcher) });
      expect(trigger.textContent).toContain("Bilgi Üniversitesi");
      expect(trigger.getAttribute("aria-expanded")).toBe("false");

      fireEvent.click(trigger);
      expect(trigger.getAttribute("aria-expanded")).toBe("true");
      const list = document.getElementById(trigger.getAttribute("aria-controls") ?? "");
      expect(list).toBeTruthy();
      const org = within(list as HTMLElement).getByRole("link", { name: "Lale Yazılım A.Ş." });
      expect(org.getAttribute("href")).toBe("/kurulus/org-1/panel");
      const inst = within(list as HTMLElement).getByRole("link", { name: "Bilgi Üniversitesi" });
      expect(inst.getAttribute("aria-current")).toBe("page");
    });

    it("bağlam seçici Esc ile kapanır ve odak düğmeye döner", () => {
      renderAt("/calismalar", {
        user: { id: "u1" },
        organizations: [{ id: "org-1", name: "Lale Yazılım A.Ş." }],
      });
      const trigger = screen.getByRole("button", { name: new RegExp(messages.shell.contextSwitcher) });
      fireEvent.click(trigger);
      fireEvent.keyDown(document, { key: "Escape" });
      expect(trigger.getAttribute("aria-expanded")).toBe("false");
      expect(document.activeElement).toBe(trigger);
    });

    it("'Profilimi gör' yalnız public slug varsa ve yeni sekmede açılır", () => {
      const { unmount } = renderAt("/profil", { user: { id: "u1" }, talent_profile: { public_slug: "ayse-yilmaz" } });
      const link = screen.getByRole("link", { name: new RegExp(messages.shell.viewPublicProfile) });
      expect(link.getAttribute("href")).toBe("/p/ayse-yilmaz");
      expect(link.getAttribute("target")).toBe("_blank");
      expect(link.getAttribute("rel")).toContain("noopener");
      unmount();

      renderAt("/profil", { user: { id: "u1" }, talent_profile: { public_slug: null } });
      expect(screen.queryByRole("link", { name: new RegExp(messages.shell.viewPublicProfile) })).toBeNull();
    });

    it("Keşfet sayfası yokken menüde görünmez", () => {
      const { container } = renderAt("/calismalar", { user: { id: "u1" }, talent_profile: { public_slug: null } });
      expect(container.innerHTML).not.toContain('href="/kesfet"');
    });

    it("kullanıcı menüsü ad, rol başlığı ve maskeli e-postayı gösterir; tam e-posta yok", () => {
      const { container } = renderAt("/calismalar", {
        user: { id: "u1", email: "ayse.yilmaz@ornek.edu.tr", full_name: "Ayşe Yılmaz" },
        talent_profile: { public_slug: null },
      });
      fireEvent.click(screen.getByRole("button", { name: messages.shell.userMenu }));
      expect(screen.getByText("Ayşe Yılmaz")).toBeTruthy();
      expect(screen.getByText(messages.shell.roleStudent)).toBeTruthy();
      expect(container.innerHTML).not.toContain("ayse.yilmaz@ornek.edu.tr");
    });

    it("mobil çekmece açılınca odak kapat düğmesine gider, Esc ile kapanır", () => {
      renderAt("/calismalar", { user: { id: "u1" }, talent_profile: { public_slug: null } });
      const open = screen.getByRole("button", { name: messages.shell.openMenu });
      fireEvent.click(open);
      const dialog = screen.getByRole("dialog", { name: messages.shell.mainNav });
      expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: messages.shell.closeMenu }));
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(document.activeElement).toBe(open);
    });
  });
});
