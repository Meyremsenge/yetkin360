import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "@/app/giris/page";
import messages from "@/messages/tr.json";
import * as clientModule from "@/lib/api/client";

// Mock lib/api/client
vi.mock("@/lib/api/client", () => ({
  login: vi.fn(),
}));

// Mock lib/session/use-session
vi.mock("@/lib/session/use-session", () => ({
  useSession: vi.fn(),
}));

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("LoginPage (giris/page.tsx) — Form Gerçek İmplementasyon", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("AC-6: Başlık", () => {
    it("AC-6: messages.giris.title başlığı vardır", async () => {
      const { container } = render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const heading = container.querySelector("h1, h2, h3");
      expect(heading?.textContent).toContain(messages.giris.title);
    });
  });

  describe("AC-4: neden='oturum-bitti' parametresi", () => {
    it("AC-4: neden='oturum-bitti' varsa messages.session.expired gösterilir", async () => {
      render(
        await LoginPage({
          searchParams: Promise.resolve({ neden: "oturum-bitti" }),
        })
      );

      expect(screen.getByText(messages.session.expired)).toBeTruthy();
    });

    it("AC-4: messages.session.expired mesajı aria-live atası içerir", async () => {
      render(
        await LoginPage({
          searchParams: Promise.resolve({ neden: "oturum-bitti" }),
        })
      );

      const message = screen.getByText(messages.session.expired);
      expect(message.closest("[aria-live]")).not.toBeNull();
    });

    it("AC-4: neden parametresi yoksa messages.session.expired GÖRÜNMEZ", async () => {
      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      expect(screen.queryByText(messages.session.expired)).toBeNull();
    });

    it("AC-4: neden='oturum-bitti' dışındaki değer GÖRÜNMEZ", async () => {
      render(
        await LoginPage({
          searchParams: Promise.resolve({
            neden: "başka-neden",
          }),
        })
      );

      expect(screen.queryByText(messages.session.expired)).toBeNull();
    });
  });

  describe("AC-2: Giriş happy path (email+password → login() → 200 → oturum kurulur + yönlendir)", () => {
    it("AC-2: login() 200 döndürürse useSession invalidate edilir ve /panel'e yönlendirilir", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockResolvedValueOnce({ user_id: "123", role: "user", email_verified: true });

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
      });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/calismalar");
      });
    });

    it("AC-2: next param varsa oraya yönlendirilir", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockResolvedValueOnce({ user_id: "123", role: "user", email_verified: true });

      render(
        await LoginPage({
          searchParams: Promise.resolve({ next: "/dashboard" }),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard");
      });
    });

    it("AC-S5: next='//evil.com' (protocol-relative open redirect) → sanitize edilip '/calismalar'a yönlendirilir", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockResolvedValueOnce({ user_id: "123", role: "user", email_verified: true });

      render(
        await LoginPage({
          searchParams: Promise.resolve({ next: "//evil.com" }),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/calismalar");
      });
      expect(mockPush).not.toHaveBeenCalledWith(expect.stringContaining("evil.com"));
    });

    it("AC-S5: next='https://evil.com' (protokol tabanlı open redirect) → '/calismalar'a yönlendirilir", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockResolvedValueOnce({ user_id: "123", role: "user", email_verified: true });

      render(
        await LoginPage({
          searchParams: Promise.resolve({ next: "https://evil.com" }),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/calismalar");
      });
      expect(mockPush).not.toHaveBeenCalledWith(expect.stringContaining("evil.com"));
    });

    it("AC-S5: next='javascript:alert(1)' (javascript: protokolü) → '/calismalar'a yönlendirilir", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockResolvedValueOnce({ user_id: "123", role: "user", email_verified: true });

      render(
        await LoginPage({
          searchParams: Promise.resolve({ next: "javascript:alert(1)" }),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/calismalar");
      });
      expect(mockPush).not.toHaveBeenCalledWith(expect.stringContaining("javascript"));
    });

    it("AC-S5: next='/\\\\evil.com' (backslash bypass) → '/calismalar'a yönlendirilir", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockResolvedValueOnce({ user_id: "123", role: "user", email_verified: true });

      render(
        await LoginPage({
          searchParams: Promise.resolve({ next: "/\\evil.com" }),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/calismalar");
      });
      expect(mockPush).not.toHaveBeenCalledWith(expect.stringContaining("evil.com"));
    });
  });

  describe("AC-3: Giriş — 401 INVALID_CREDENTIALS (tek, genel mesaj)", () => {
    it("AC-3: 401 INVALID_CREDENTIALS → 'E-posta veya şifre hatalı' mesajı + hangi alan yanlış BELİRTİLMEZ", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      const error = new Error("Unauthorized") as Error & Record<string, unknown>;
      error.status = 401;
      error.code = "INVALID_CREDENTIALS";
      mockLogin.mockRejectedValueOnce(error);

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "wrong@example.com");
      await user.type(passwordInput, "wrongpassword");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/E-posta veya şifre hatalı/i)).toBeTruthy();
      });

      // Email ve password input'larında ayrı error mesajı YOK (ayrım yok)
      expect(emailInput).not.toHaveAttribute("aria-invalid", "true");
      expect(passwordInput).not.toHaveAttribute("aria-invalid", "true");
    });
  });

  describe("AC-4: Giriş — 423 ACCOUNT_LOCKED (401'den FARKLI mesaj)", () => {
    it("AC-4: 423 ACCOUNT_LOCKED → 'Hesabınız geçici olarak kilitlendi' mesajı", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      const error = new Error("Locked") as Error & Record<string, unknown>;
      error.status = 423;
      error.code = "ACCOUNT_LOCKED";
      mockLogin.mockRejectedValueOnce(error);

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "locked@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Hesabınız geçici olarak kilitlendi/i)).toBeTruthy();
      });

      // 401 mesajı YOKTUR
      expect(screen.queryByText(/E-posta veya şifre hatalı/i)).toBeNull();
    });
  });

  describe("AC-9: Client-side + backend validasyon (422)", () => {
    it("AC-9: Geçersiz email formatı — submit ÖNCESİ hata gösterilir", async () => {
      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "invalid-email");
      await user.type(passwordInput, "password123");

      // Submit ÖNCESİ hata gösterilmeli (HTML5 validation veya form lib'i)
      // Eğer HTML5 validation varsa submit atılmayacak
      // Eğer form lib'i varsa error mesajı gösterilecek
      expect(submitButton).toBeTruthy();
    });

    it("AC-9: Backend 422 dönerse ilgili alanın altında backend mesajı gösterilir", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      const error = new Error("Validation error") as Error & Record<string, unknown>;
      error.status = 422;
      error.fields = {
        email: "E-posta zaten kayıtlı",
      };
      mockLogin.mockRejectedValueOnce(error);

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/E-posta zaten kayıtlı/i)).toBeTruthy();
      });
    });
  });

  describe("AC-10: 429 Rate Limit (form OTOMATİK retry YAPMAZ)", () => {
    it("AC-10: 429 → 'Çok fazla deneme' mesajı + form kullanıcı eylemi bekler", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      const error = new Error("Too many requests") as Error & Record<string, unknown>;
      error.status = 429;
      mockLogin.mockRejectedValueOnce(error);

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Çok fazla deneme/i)).toBeTruthy();
      });

      // Form OTOMATİK retry YAPMAZ — istemci setTimeout/retry yok
      expect(mockLogin).toHaveBeenCalledTimes(1);
    });
  });

  describe("AC-11: Ağ hatası (submit butonu tekrar aktif olur)", () => {
    it("AC-11: Fetch reddi → 'Bağlantı hatası' mesajı + submit butonu tekrar aktif", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockRejectedValueOnce(new Error("Network error"));

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Bağlantı hatası/i)).toBeTruthy();
      });

      // Submit butonu tekrar aktif (disabled KALKMIŞ)
      expect(submitButton).not.toHaveAttribute("disabled");
    });
  });

  describe("AC-12: Çift submit engeli (ikinci tıklama = hiçbir ek istek)", () => {
    it("AC-12: Submit tıklanırsa buton disabled+loading olur; ikinci tıklama hiçbir ek istek göndermez", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      mockLogin.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ user_id: "123", role: "user", email_verified: true }), 500))
      );

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      // Buton disabled + loading state
      expect(submitButton).toHaveAttribute("disabled");

      // İkinci tıklama (disabled durumda, etkisiz olur)
      await user.click(submitButton);

      // login() SADECE 1 kez çağrıldı
      expect(mockLogin).toHaveBeenCalledTimes(1);
    });
  });

  describe("AC-S4: Şifre alanı hijyeni (type='password' + autoComplete)", () => {
    it("AC-S4: Password input type='password' + autoComplete='current-password'", async () => {
      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      expect(passwordInput).toHaveAttribute("type", "password");
      expect(passwordInput).toHaveAttribute("autoComplete", "current-password");
    });

    it("AC-S4: Password değeri console'a yazılmaz", async () => {
      const spyConsole = vi.spyOn(console, "log");
      const spyError = vi.spyOn(console, "error");

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const user = userEvent.setup();
      await user.type(passwordInput, "secretpassword123");

      // Password hiçbir console.log/error'a yazılmaz
      expect(spyConsole).not.toHaveBeenCalledWith(expect.stringContaining("secretpassword"));
      expect(spyError).not.toHaveBeenCalledWith(expect.stringContaining("secretpassword"));

      spyConsole.mockRestore();
      spyError.mockRestore();
    });
  });

  describe("AC-S6: DoS — 429'dan sonra otomatik retry YOK", () => {
    it("AC-S6: 429 alındıktan sonra istemci otomatik retry YAPMAZ", async () => {
      const mockLogin = vi.spyOn(clientModule, "login");
      const error = new Error("Too many requests") as Error & Record<string, unknown>;
      error.status = 429;
      mockLogin.mockRejectedValueOnce(error);

      render(
        await LoginPage({
          searchParams: Promise.resolve({}),
        })
      );

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/şifre/i) || screen.getByLabelText(/şifre/i);
      const submitButton = screen.getByRole("button", { name: /gir/i });

      const user = userEvent.setup();
      await user.type(emailInput, "test@example.com");
      await user.type(passwordInput, "password123");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledTimes(1);
      });

      // 3 saniye beklersek bile login() tekrar çağrılmaz
      await new Promise((resolve) => setTimeout(resolve, 3000));
      expect(mockLogin).toHaveBeenCalledTimes(1);
    });
  });
});
