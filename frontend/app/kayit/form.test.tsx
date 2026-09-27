import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegisterForm from "@/app/kayit/form";
import { useRouter } from "next/navigation";
import * as clientApi from "@/lib/api/client";

// Mock dependencies
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  register: vi.fn(),
}));

describe("RegisterForm (kayit/form.tsx)", () => {
  const mockPush = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
    } as unknown as ReturnType<typeof useRouter>);
  });

  afterEach(() => {
    cleanup();
  });

  // =========================================================================
  // AC-1/AC-4: Kayıt başarılı — başarı mesajı role="status" ile duyurulabilir
  // =========================================================================

  it("AC-1/AC-4: kayıt başarılı — başarı mesajı role='status' ile bulunabilir", async () => {
    vi.mocked(clientApi.register).mockResolvedValueOnce(undefined);

    const user = userEvent.setup();
    render(<RegisterForm />);

    // Form alanlarını doldur
    const emailInput = screen.getByLabelText(/e-posta/i);
    const passwordInput = screen.getByLabelText(/^şifre$/i);
    const passwordConfirmInput = screen.getByLabelText(/şifre tekrar/i);
    const fullNameInput = screen.getByLabelText(/ad soyad/i);

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "SecurePass123!");
    await user.type(passwordConfirmInput, "SecurePass123!");
    await user.type(fullNameInput, "Test User");

    // Gönder
    const submitButton = screen.getByRole("button", { name: /kayıt ol|gönder/i });
    await user.click(submitButton);

    // Başarı mesajı role="status" ile duyurulabilir olmalı
    await waitFor(() => {
      const successMsg = screen.getByRole("status");
      expect(successMsg).toBeTruthy();
      expect(successMsg.textContent).toBeTruthy();
    });

    // Başarı mesajı gösterildikten sonra yönlendirme yapılmalı
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/giris");
    }, { timeout: 1000 });
  });

  it("AC-1/AC-4: başarı mesajı görsel stil korunur (regresyon: yeşil, kenarlık, metni)", async () => {
    vi.mocked(clientApi.register).mockResolvedValueOnce(undefined);

    const user = userEvent.setup();
    const { container } = render(<RegisterForm />);

    // Form doldur ve gönder
    const emailInput = screen.getByLabelText(/e-posta/i);
    const passwordInput = screen.getByLabelText(/^şifre$/i);
    const passwordConfirmInput = screen.getByLabelText(/şifre tekrar/i);
    const fullNameInput = screen.getByLabelText(/ad soyad/i);

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "SecurePass123!");
    await user.type(passwordConfirmInput, "SecurePass123!");
    await user.type(fullNameInput, "Test User");

    const submitButton = screen.getByRole("button", { name: /kayıt ol|gönder/i });
    await user.click(submitButton);

    // Başarı mesajı gösterilir — yeşil stilini kontrol et
    await waitFor(() => {
      const successMsg = screen.getByRole("status");
      // bg-green-50, border-green-200 sınıflarını dış div'de kontrol et
      expect(successMsg.className).toContain("bg-green-50");
      expect(successMsg.className).toContain("border-green-200");
      // text-green-700 sınıfını içindeki <p> elemanında kontrol et
      const paragraph = successMsg.querySelector("p");
      expect(paragraph?.className).toContain("text-green-700");
    });
  });

  it("Form — şifreler uyuşmamalı", async () => {
    vi.mocked(clientApi.register).mockResolvedValueOnce(undefined);

    const user = userEvent.setup();
    render(<RegisterForm />);

    const emailInput = screen.getByLabelText(/e-posta/i);
    const passwordInput = screen.getByLabelText(/^şifre$/i);
    const passwordConfirmInput = screen.getByLabelText(/şifre tekrar/i);
    const fullNameInput = screen.getByLabelText(/ad soyad/i);

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "SecurePass123!");
    await user.type(passwordConfirmInput, "DifferentPass123!"); // Uyuşmayan
    await user.type(fullNameInput, "Test User");

    const submitButton = screen.getByRole("button", { name: /kayıt ol|gönder/i });
    await user.click(submitButton);

    // Hata mesajı gösterilmelidir
    await waitFor(() => {
      expect(
        screen.queryByText(/eşleşmiyor|uyuşmuyor/i) ||
          screen.queryByText(/match/i)
      ).toBeTruthy();
    });

    // API çağrılmaz
    expect(vi.mocked(clientApi.register)).not.toHaveBeenCalled();
  });
});
