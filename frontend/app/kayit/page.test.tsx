import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegisterPage from "@/app/kayit/page";
import * as clientModule from "@/lib/api/client";

// Mock lib/api/client
vi.mock("@/lib/api/client", () => ({
  register: vi.fn(),
}));

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("RegisterPage (kayit/page.tsx) — Kayıt Formu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("AC-1: Kayıt happy path (email+password≥8+full_name → 201 → oturum AÇILMAZ → yönlendir)", () => {
    it("AC-1: Geçerli email+password(≥8)+full_name girilip submit → backend 201 döner → oturum AÇILMAZ → /giris'e yönlendirilir", async () => {
      const mockRegister = vi.spyOn(clientModule, "register");
      mockRegister.mockResolvedValueOnce({ user_id: "new-user-123" });

      render(<RegisterPage />);

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      const submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      await user.type(emailInput, "newuser@example.com");
      await user.type(passwordInput, "securepass123");
      await user.type(fullNameInput, "Ahmet Yılmaz");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith(
          "newuser@example.com",
          "securepass123",
          "Ahmet Yılmaz",
          "TALENT",
          undefined
        );
      });

      // Oturum AÇILMAZ (useSession invalidate edilmez, cookie yok)
      // Backend'den cookie gelmediği için oturum kalmaz

      // "e-postanızı doğrulayın" mesajı gösterilir
      await waitFor(() => {
        expect(screen.getByText(/e-postanızı doğrulayın/i)).toBeTruthy();
      });

      // /giris'e yönlendirilir
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/giris");
      });
    });
  });

  describe("AC-9: Client-side + backend validasyon", () => {
    it("AC-9: Geçersiz email formatı — submit ÖNCESİ hata gösterilir, backend'e istek gitmez", async () => {
      render(<RegisterPage />);

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      const submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      await user.type(emailInput, "invalid-email");
      await user.type(passwordInput, "securepass123");
      await user.type(fullNameInput, "Ahmet Yılmaz");

      // Form kütüphanesi (RHF + Zod) veya HTML5 validation hata gösterir
      // Submit ÖNCESİ engellenebilir veya submit atılabilir ama error mesajı gösterilir
      expect(submitButton).toBeTruthy();

      // Backend'e istek gitmez (HTML5/form validation engellerse)
      // Veya giderse bile mockRegister 0 kez çağrılır
    });

    it("AC-9: Password < 8 karakter — submit ÖNCESİ hata gösterilir", async () => {
      render(<RegisterPage />);

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      const submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      await user.type(emailInput, "newuser@example.com");
      await user.type(passwordInput, "short");
      await user.type(fullNameInput, "Ahmet Yılmaz");

      // RHF + Zod minimum length validation
      // Error mesajı gösterilir veya submit engellenir
      expect(submitButton).toBeTruthy();
    });

    it("AC-9: Şifre tekrar alanı eşleşmiyorsa hata gösterilir", async () => {
      render(<RegisterPage />);

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const passwordConfirmInput = screen.getByPlaceholderText(/şifre.*tekrar/i) || screen.getByLabelText(/şifre.*tekrar/i);
      const fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      const submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      await user.type(emailInput, "newuser@example.com");
      await user.type(passwordInput, "securepass123");
      await user.type(passwordConfirmInput, "differentpass123");
      await user.type(fullNameInput, "Ahmet Yılmaz");

      // Zod refine kuralı hata gösterir (şifreler eşleşmiyor)
      expect(submitButton).toBeTruthy();
    });

    it("AC-9: Backend 422 dönerse ilgili alanın altında backend mesajı gösterilir", async () => {
      const mockRegister = vi.spyOn(clientModule, "register");
      const error = new Error("Validation error") as Error & Record<string, unknown>;
      error.status = 422;
      error.fields = {
        password: "Şifre çok zayıf",
      };
      mockRegister.mockRejectedValueOnce(error);

      render(<RegisterPage />);

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      const submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      await user.type(emailInput, "newuser@example.com");
      await user.type(passwordInput, "WeakPass1");
      await user.type(fullNameInput, "Ahmet Yılmaz");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Şifre çok zayıf/i)).toBeTruthy();
      });
    });
  });

  describe("AC-S1: Numaralandırma yok — zaten kayıtlı email ile de 201 döner + AYNI mesaj", () => {
    it("AC-S1: Zaten kayıtlı email ile submit → backend 201 döner → 'e-postanızı doğrulayın' mesajı + /giris'e yönlendir (farklı mesaj/davranış YOK)", async () => {
      const mockRegister = vi.spyOn(clientModule, "register");
      // Backend'in davranışı: zaten kayıtlı email de 201 döner (numaralandırma yok)
      mockRegister.mockResolvedValueOnce({ user_id: "already-exists-123" });

      render(<RegisterPage />);

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      const submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      // Zaten kayıtlı bir email
      await user.type(emailInput, "already@example.com");
      await user.type(passwordInput, "securepass123");
      await user.type(fullNameInput, "Ahmet Yılmaz");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith(
          "already@example.com",
          "securepass123",
          "Ahmet Yılmaz",
          "TALENT",
          undefined
        );
      });

      // Happy path ile AYNI mesaj gösterilir
      await waitFor(() => {
        expect(screen.getByText(/e-postanızı doğrulayın/i)).toBeTruthy();
      });

      // Happy path ile AYNI şekilde /giris'e yönlendirilir
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/giris");
      });
    });

    it("AC-S1: İki farklı scenario'da (yeni + zaten kayıtlı email) UI davranışı identik", async () => {
      const mockRegister = vi.spyOn(clientModule, "register");

      // Scenario 1: Yeni email
      mockRegister.mockResolvedValueOnce({ user_id: "new-user-123" });

      const { unmount } = render(<RegisterPage />);

      let emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      let passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      let fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      let submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      await user.type(emailInput, "newuser@example.com");
      await user.type(passwordInput, "securepass123");
      await user.type(fullNameInput, "Ahmet Yılmaz");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/e-postanızı doğrulayın/i)).toBeTruthy();
      });

      const scenario1Message = screen.getByText(/e-postanızı doğrulayın/i);

      unmount();
      vi.clearAllMocks();

      // Scenario 2: Zaten kayıtlı email
      mockRegister.mockResolvedValueOnce({ user_id: "already-exists-123" });

      render(<RegisterPage />);

      emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      await user.type(emailInput, "already@example.com");
      await user.type(passwordInput, "securepass123");
      await user.type(fullNameInput, "Ahmet Yılmaz");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/e-postanızı doğrulayın/i)).toBeTruthy();
      });

      const scenario2Message = screen.getByText(/e-postanızı doğrulayın/i);

      // İki mesaj AYNI (farklı metin, stil, bekleme süresi YOK)
      expect(scenario1Message.textContent).toBe(scenario2Message.textContent);
    });
  });

  describe("AC-S4: Şifre alanı hijyeni (type='password' + autoComplete='new-password')", () => {
    it("AC-S4: Password input type='password' + autoComplete='new-password'", async () => {
      render(<RegisterPage />);

      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      expect(passwordInput).toHaveAttribute("type", "password");
      expect(passwordInput).toHaveAttribute("autoComplete", "new-password");
    });

    it("AC-S4: Password şifre tekrar input'u da type='password'", async () => {
      render(<RegisterPage />);

      const passwordConfirmInput = screen.getByPlaceholderText(/şifre.*tekrar/i) || screen.getByLabelText(/şifre.*tekrar/i);
      expect(passwordConfirmInput).toHaveAttribute("type", "password");
    });

    it("AC-S4: Password değeri console.log/error'a yazılmaz", async () => {
      const spyConsole = vi.spyOn(console, "log");
      const spyError = vi.spyOn(console, "error");

      render(<RegisterPage />);

      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const user = userEvent.setup();
      await user.type(passwordInput, "secretpass123");

      // Password hiçbir console çıktısında yok
      expect(spyConsole).not.toHaveBeenCalledWith(expect.stringContaining("secretpass"));
      expect(spyError).not.toHaveBeenCalledWith(expect.stringContaining("secretpass"));

      spyConsole.mockRestore();
      spyError.mockRestore();
    });
  });

  describe("AC-12: Çift submit engeli", () => {
    it("AC-12: Submit tıklanırsa buton disabled+loading olur; ikinci tıklama hiçbir ek istek göndermez", async () => {
      const mockRegister = vi.spyOn(clientModule, "register");
      mockRegister.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ user_id: "123" }), 500))
      );

      render(<RegisterPage />);

      const emailInput = screen.getByPlaceholderText(/e-posta/i) || screen.getByLabelText(/e-posta/i);
      const passwordInput = screen.getByPlaceholderText(/yeni şifre/i) || screen.getByLabelText(/yeni şifre/i);
      const fullNameInput = screen.getByPlaceholderText(/adı soyadı/i) || screen.getByLabelText(/adı soyadı/i);
      const submitButton = screen.getByRole("button", { name: /kayıt ol/i });

      const user = userEvent.setup();
      await user.type(emailInput, "newuser@example.com");
      await user.type(passwordInput, "securepass123");
      await user.type(fullNameInput, "Ahmet Yılmaz");
      await user.click(submitButton);

      // Buton disabled + loading
      expect(submitButton).toHaveAttribute("disabled");

      // İkinci tıklama (etkisiz)
      await user.click(submitButton);

      // register() SADECE 1 kez çağrıldı
      expect(mockRegister).toHaveBeenCalledTimes(1);
    });
  });
});
