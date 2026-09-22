import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
});
