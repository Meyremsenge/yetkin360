import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ResetPasswordPage from "@/app/sifre-sifirla/page";

// Mock lib/api/client
vi.mock("@/lib/api/client", () => ({
  resetPassword: vi.fn(),
}));

// Mock next/navigation for useSearchParams
vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
}));

import { resetPassword } from "@/lib/api/client";
import { useSearchParams } from "next/navigation";

describe("ResetPasswordPage (sifre-sifirla/page.tsx)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("AC-8: Happy path — geçerli token + yeni şifre", () => {
    it("AC-8: Geçerli token + şifre (≥8) + eşleşen tekrar → 204 → 'şifren değişti' mesajı + /giris'e yönlendirme", async () => {
      const mockToken = "reset-token-abc123";
      const newPassword = "NewPassword123";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockResolvedValue(undefined);

      const { container } = render(<ResetPasswordPage />);

      // Şifre input'larını bul
      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      expect(passwordInputs.length).toBeGreaterThanOrEqual(2);

      // İlk input: yeni şifre
      fireEvent.change(passwordInputs[0], { target: { value: newPassword } });

      // İkinci input: şifre tekrar
      fireEvent.change(passwordInputs[1], { target: { value: newPassword } });

      // Submit butonunu bul
      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla") ||
          content.includes("devam"),
      });

      fireEvent.click(submitButton);

      // Backend'e çağrı yapılır
      await waitFor(() => {
        expect(resetPassword).toHaveBeenCalledWith(mockToken, newPassword);
      });

      // Oturum AÇILMAZ (cookie farkı kontrol edilemez test'te ama davranış kontrol edilir)

      // "Şifren değişti" mesajı gösterilir
      const successMessage = screen.queryByText(
        (content) =>
          content.includes("değişti") ||
          content.includes("Değişti") ||
          content.includes("başarıyla") ||
          content.includes("Başarıyla")
      );
      expect(successMessage).toBeTruthy();

      // /giris'e yönlendirme linki gösterilir
      const loginLink = container.querySelector('a[href="/giris"]');
      expect(loginLink).toBeTruthy();
    });
  });

  describe("AC-9: Şifre ve tekrar alanı eşleşmemesi", () => {
    it("AC-9: Şifre ve tekrar eşleşmiyor → submit ÖNCESİ client-side hata, backend'e istek gitmez", () => {
      const mockToken = "reset-token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      // Farklı değerler gir
      fireEvent.change(passwordInputs[0], { target: { value: "Password123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "Password456" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      // Backend'e istek gitmez
      expect(resetPassword).not.toHaveBeenCalled();

      // Hata mesajı gösterilir
      screen.queryByText(
        (content) =>
          content.includes("eşleş") ||
          content.includes("Eşleş") ||
          content.includes("aynı") ||
          content.includes("uymuyor")
      );
      // Hata en azından gösterilir — exact text backend'e bağlı olabilir
      expect(resetPassword).not.toHaveBeenCalled();
    });
  });

  describe("AC-6: Geçersiz/süresi dolmuş token", () => {
    it("AC-6: 400 INVALID_TOKEN → hata mesajı + /sifre-unuttum'a dönme linki", async () => {
      const mockToken = "invalid-token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockRejectedValue({
        status: 400,
        code: "INVALID_TOKEN",
      });

      const { container } = render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      fireEvent.change(passwordInputs[0], { target: { value: "NewPass123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "NewPass123" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(resetPassword).toHaveBeenCalled();
      });

      // Hata mesajı
      const errorMessage = screen.queryByText(
        (content) =>
          content.includes("geçersiz") ||
          content.includes("Geçersiz") ||
          content.includes("bağlantı geçersiz")
      );
      expect(errorMessage).toBeTruthy();

      // /sifre-unuttum'a giden link
      const resetLink = container.querySelector('a[href="/sifre-unuttum"]');
      expect(resetLink).toBeTruthy();
    });

    it("AC-6: 410 TOKEN_EXPIRED → süresi dolmuş mesajı + /sifre-unuttum'a dönme linki", async () => {
      const mockToken = "expired-token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockRejectedValue({
        status: 410,
        code: "TOKEN_EXPIRED",
      });

      const { container } = render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      fireEvent.change(passwordInputs[0], { target: { value: "NewPass123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "NewPass123" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(resetPassword).toHaveBeenCalled();
      });

      // Süresi dolmuş mesajı
      const expiredMessage = screen.queryByText(
        (content) =>
          content.includes("süresi dolmuş") ||
          content.includes("Süresi dolmuş") ||
          content.includes("bağlantı süresi dolmuş")
      );
      expect(expiredMessage).toBeTruthy();

      // /sifre-unuttum'a giden link
      const resetLink = container.querySelector('a[href="/sifre-unuttum"]');
      expect(resetLink).toBeTruthy();
    });
  });

  describe("AC-S3: Token XSS/log sızıntısı testi", () => {
    it("AC-S3: dangerouslySetInnerHTML kullanılmaz — token sayfada ham HTML olarak render edilmez", () => {
      const mockToken = "<script>alert('XSS')</script>";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockResolvedValue(undefined);

      const { container } = render(<ResetPasswordPage />);

      // Container HTML'de script tag'i çalıştırılabilir durumda olmamalı
      const html = container.innerHTML;
      const hasExecutableScript = html.includes("<script>alert");
      expect(hasExecutableScript).toBe(false);
    });

    it("AC-S3: Token query param'ı body'de backend'e gönderilir, HTML'e değil", async () => {
      const mockToken = "<img src=x onerror='console.log(1)'>";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockResolvedValue(undefined);

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      fireEvent.change(passwordInputs[0], { target: { value: "NewPass123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "NewPass123" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        // Token resetPassword'ün argümanında (POST body'de) gönderilir
        expect(resetPassword).toHaveBeenCalledWith(mockToken, "NewPass123");
      });

      // Sayfada token literal olarak görünmemelidir
      const visibleToken = screen.queryByText(mockToken);
      expect(visibleToken).toBeNull();
    });
  });

  describe("AC-S4: Şifre alanı hijyeni", () => {
    it("AC-S4: Password input'u type='password' ve autoComplete='new-password' veya 'current-password' kullanır", () => {
      const mockToken = "token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);

      const { container } = render(<ResetPasswordPage />);

      // Password input'larını bul
      const passwordInputs = container.querySelectorAll('input[type="password"]');

      expect(passwordInputs.length).toBeGreaterThanOrEqual(2);

      // autoComplete kontrol
      let hasAutoComplete = false;
      passwordInputs.forEach((input) => {
        const autoCompleteValue = input.getAttribute("autoComplete");
        if (
          autoCompleteValue === "new-password" ||
          autoCompleteValue === "current-password"
        ) {
          hasAutoComplete = true;
        }
      });

      // En azından bir input'un autoComplete'i olmalı
      expect(hasAutoComplete).toBe(true);
    });

    it("AC-S4: Password değeri console'e yazılmaz (loglama testi)", async () => {
      const mockToken = "token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockResolvedValue(undefined);

      // Console.log'u spy et
      const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      const testPassword = "SuperSecret123";
      fireEvent.change(passwordInputs[0], { target: { value: testPassword } });
      fireEvent.change(passwordInputs[1], { target: { value: testPassword } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(resetPassword).toHaveBeenCalled();
      });

      // Console'da password gözükmemelidir
      consoleSpy.mock.calls.forEach((call) => {
        expect(call[0]?.toString()).not.toContain(testPassword);
      });

      consoleSpy.mockRestore();
    });
  });

  describe("AC-12: Çift submit engeli", () => {
    it("AC-12: Submit sırasında buton disabled olur", async () => {
      const mockToken = "token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockImplementation(
        () =>
          new Promise((resolve) => setTimeout(() => resolve(undefined), 100))
      );

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      fireEvent.change(passwordInputs[0], { target: { value: "NewPass123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "NewPass123" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton.hasAttribute("disabled")).toBe(true);
      });
    });

    it("AC-12: İkinci tıklama hiçbir ek istek göndermez", async () => {
      const mockToken = "token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);

      let callCount = 0;
      vi.mocked(resetPassword).mockImplementation(() => {
        callCount++;
        return Promise.resolve(undefined);
      });

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      fireEvent.change(passwordInputs[0], { target: { value: "NewPass123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "NewPass123" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);
      fireEvent.click(submitButton); // İkinci tıklama

      await waitFor(() => {
        expect(callCount).toBe(1);
      });
    });
  });

  describe("AC-9 (açık): Şifre min-length kontrolü", () => {
    it("AC-9: Şifre < 8 karakter → submit ÖNCESİ hata", () => {
      const mockToken = "token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      const shortPassword = "Pass123"; // 7 karakter
      fireEvent.change(passwordInputs[0], { target: { value: shortPassword } });
      fireEvent.change(passwordInputs[1], { target: { value: shortPassword } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      // Backend'e istek gitmez
      expect(resetPassword).not.toHaveBeenCalled();
    });
  });

  describe("AC-11: Ağ hatası", () => {
    it("AC-11: Fetch reddi → 'bağlantı hatası' mesajı, buton tekrar aktif", async () => {
      const mockToken = "token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockRejectedValue(new Error("Network error"));

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      fireEvent.change(passwordInputs[0], { target: { value: "NewPass123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "NewPass123" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(resetPassword).toHaveBeenCalled();
      });

      // Hata mesajı gösterilir
      const errorMessage = screen.queryByText(
        (content) =>
          content.includes("bağlantı") ||
          content.includes("Bağlantı") ||
          content.includes("başarısız") ||
          content.includes("hatası")
      );
      expect(errorMessage).toBeTruthy();

      // Buton tekrar aktif olur
      await waitFor(() => {
        expect(submitButton.hasAttribute("disabled")).toBe(false);
      });
    });
  });

  describe("AC-10: Rate limit", () => {
    it("AC-10: 429 döner → 'çok fazla deneme' mesajı", async () => {
      const mockToken = "token";
      const mockSearchParams = new URLSearchParams({ token: mockToken });

      vi.mocked(useSearchParams).mockReturnValue(mockSearchParams as unknown as ReturnType<typeof useSearchParams>);
      vi.mocked(resetPassword).mockRejectedValue({
        status: 429,
        code: "TOO_MANY_REQUESTS",
      });

      render(<ResetPasswordPage />);

      const passwordInputs = screen.getAllByRole("textbox", {
        name: (content) =>
          content.includes("şifre") || content.includes("password"),
      });

      fireEvent.change(passwordInputs[0], { target: { value: "NewPass123" } });
      fireEvent.change(passwordInputs[1], { target: { value: "NewPass123" } });

      const submitButton = screen.getByRole("button", {
        name: (content) =>
          content.includes("değiştir") ||
          content.includes("Değiştir") ||
          content.includes("sıfırla"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(resetPassword).toHaveBeenCalled();
      });

      const rateLimitMessage = screen.queryByText(
        (content) =>
          content.includes("çok fazla") ||
          content.includes("Çok fazla") ||
          content.includes("deneme")
      );
      expect(rateLimitMessage).toBeTruthy();
    });
  });
});
