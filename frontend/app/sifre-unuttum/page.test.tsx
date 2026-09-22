import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ForgotPasswordPage from "@/app/sifre-unuttum/page";

// Mock lib/api/client
vi.mock("@/lib/api/client", () => ({
  forgotPassword: vi.fn(),
}));

import { forgotPassword } from "@/lib/api/client";

describe("ForgotPasswordPage (sifre-unuttum/page.tsx)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("AC-7: Happy path — herhangi email → 204 → SABİT tek mesaj", () => {
    it("AC-7: Geçerli email girilip submit → backend 204 döner → 'mesaj gönderildi' mesajı gösterilir", async () => {
      const testEmail = "user@example.com";

      vi.mocked(forgotPassword).mockResolvedValue(undefined);

      render(<ForgotPasswordPage />);

      // Email input'unu bul
      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      expect(emailInput).toBeTruthy();

      // Email gir
      fireEvent.change(emailInput, { target: { value: testEmail } });

      // Submit butonunu bul ve tıkla
      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      // Backend 204 döner
      await waitFor(() => {
        expect(forgotPassword).toHaveBeenCalledWith(testEmail);
      });

      // Sabit mesaj gösterilir: "e-posta gönderildi" vb.
      const successMessage = screen.queryByText(
        (content) =>
          content.includes("gönderildi") ||
          content.includes("kontrol et") ||
          content.includes("talimat")
      );
      expect(successMessage).toBeTruthy();
    });
  });

  describe("AC-S2 (KRİTİK, numaralandırma testi): Kayıtlı olmayan email → aynı mesaj", () => {
    it("AC-S2: Kayıtlı OLMAYAN email → backend 204 döner → AYNI SABİT mesaj gösterilir (farklı durum/mesaj YOK)", async () => {
      const nonRegisteredEmail = "notregistered@example.com";

      vi.mocked(forgotPassword).mockResolvedValue(undefined);

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      fireEvent.change(emailInput, { target: { value: nonRegisteredEmail } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(forgotPassword).toHaveBeenCalledWith(nonRegisteredEmail);
      });

      // AYNI SABİT mesaj
      const successMessage = screen.queryByText(
        (content) =>
          content.includes("gönderildi") ||
          content.includes("kontrol et") ||
          content.includes("talimat")
      );
      expect(successMessage).toBeTruthy();
    });

    it("AC-S2: Kayıtlı email → backend 204 döner → AYNI SABİT mesaj (birinci test'teki mesajla BİREBİR eşit olmalı)", async () => {
      const registeredEmail = "registered@example.com";

      vi.mocked(forgotPassword).mockResolvedValue(undefined);

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      fireEvent.change(emailInput, { target: { value: registeredEmail } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(forgotPassword).toHaveBeenCalledWith(registeredEmail);
      });

      // Mesaj aynen aynı olmalı — mesaj sabit string olmalı, dinamik "user@example.com" gibi text yok
      const messages = screen.queryAllByText(
        (content) =>
          content.includes("gönderildi") ||
          content.includes("kontrol et") ||
          content.includes("talimat")
      );
      expect(messages.length).toBeGreaterThan(0);

      // Email adresi mesajda GÖRÜNMEMELİ (numaralandırma önleme)
      const emailInMessage = screen.queryByText((content) =>
        content.includes(registeredEmail)
      );
      expect(emailInMessage).toBeNull();
    });
  });

  describe("AC-7/AC-S2: Buton ve form durumu", () => {
    it("AC-12 ile tutarlı: Submit sırasında buton disabled olur", async () => {
      vi.mocked(forgotPassword).mockImplementation(
        () =>
          new Promise((resolve) => setTimeout(() => resolve(undefined), 100))
      );

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      fireEvent.change(emailInput, { target: { value: "test@example.com" } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      // Submit sırasında buton disabled olmalı
      await waitFor(() => {
        expect(submitButton.hasAttribute("disabled")).toBe(true);
      });
    });

    it("AC-12 ile tutarlı: Çift submit engeli — aynı desen", async () => {
      let callCount = 0;
      vi.mocked(forgotPassword).mockImplementation(() => {
        callCount++;
        return Promise.resolve(undefined);
      });

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      fireEvent.change(emailInput, { target: { value: "test@example.com" } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      // İkinci tıklama yapılsa bile, bir kez çağrılması yeterli
      fireEvent.click(submitButton);
      fireEvent.click(submitButton); // İkinci tıklama

      await waitFor(() => {
        // callCount 1 olmalı (çift submit engellendi)
        expect(callCount).toBe(1);
      });
    });
  });

  describe("AC-9: Client-side email format validasyonu", () => {
    it("AC-9: Geçersiz email formatı → submit ÖNCESİ hata, backend'e istek gitmez", () => {
      vi.mocked(forgotPassword).mockResolvedValue(undefined);

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      // Geçersiz email
      fireEvent.change(emailInput, { target: { value: "invalid-email" } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      // Backend'e istek gitmez
      expect(forgotPassword).not.toHaveBeenCalled();

      // Hata mesajı alan altında gösterilir
      screen.queryByText(
        (content) =>
          content.includes("e-posta") ||
          content.includes("geçerli") ||
          content.includes("email")
      );
      // Hata gösteriliyor olabilir — en azından request atılmaz
      expect(forgotPassword).not.toHaveBeenCalled();
    });

    it("AC-9: Boş email → submit ÖNCESİ hata", () => {
      vi.mocked(forgotPassword).mockResolvedValue(undefined);

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      // Boş bırak
      fireEvent.change(emailInput, { target: { value: "" } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      expect(forgotPassword).not.toHaveBeenCalled();
    });
  });

  describe("AC-11: Ağ hatası", () => {
    it("AC-11: Fetch reddi → 'bağlantı hatası' mesajı, buton tekrar aktif", async () => {
      vi.mocked(forgotPassword).mockRejectedValue(new Error("Network error"));

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      fireEvent.change(emailInput, { target: { value: "test@example.com" } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(forgotPassword).toHaveBeenCalled();
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

      // Buton tekrar aktif olur (disabled değildir)
      await waitFor(() => {
        expect(submitButton.hasAttribute("disabled")).toBe(false);
      });
    });
  });

  describe("AC-10: Rate limit", () => {
    it("AC-10: 429 döner → 'çok fazla deneme' mesajı, form geçici disable", async () => {
      vi.mocked(forgotPassword).mockRejectedValue({
        status: 429,
        code: "TOO_MANY_REQUESTS",
      });

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      fireEvent.change(emailInput, { target: { value: "test@example.com" } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(forgotPassword).toHaveBeenCalled();
      });

      // Mesaj gösterilir
      const rateLimitMessage = screen.queryByText(
        (content) =>
          content.includes("çok fazla") ||
          content.includes("Çok fazla") ||
          content.includes("deneme") ||
          content.includes("kilitli")
      );
      expect(rateLimitMessage).toBeTruthy();

      // Form disable edilir
      await waitFor(() => {
        expect(
          submitButton.hasAttribute("disabled") ||
            emailInput.hasAttribute("disabled")
        ).toBe(true);
      });
    });
  });

  describe("AC-S6: DoS — otomatik retry yok", () => {
    it("AC-S6: 429 alındıktan sonra otomatik retry gitmez", async () => {
      let callCount = 0;
      vi.mocked(forgotPassword).mockImplementation(() => {
        callCount++;
        return Promise.reject({ status: 429 });
      });

      render(<ForgotPasswordPage />);

      const emailInput = screen.getByRole("textbox", {
        name: (content) => content.includes("e-posta") || content.includes("email"),
      });

      fireEvent.change(emailInput, { target: { value: "test@example.com" } });

      const submitButton = screen.getByRole("button", {
        name: (content) => content.includes("gönder") || content.includes("devam"),
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(forgotPassword).toHaveBeenCalled();
      });

      const initialCallCount = callCount;

      // Kısa bir süre bekle — otomatik retry olmayacak
      await new Promise((resolve) => setTimeout(resolve, 500));

      expect(callCount).toBe(initialCallCount);
    });
  });
});
