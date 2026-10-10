import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegisterForm from "@/app/kayit/form";
import { useRouter } from "next/navigation";
import * as clientApi from "@/lib/api/client";
import messages from "@/messages/tr.json";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  register: vi.fn(),
}));

const MERSIS = "0123456789012345";

async function chooseOrganization(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("radio", { name: /^Kuruluş/ }));
}

async function fillAccount(user: ReturnType<typeof userEvent.setup>, email: string) {
  await user.type(screen.getByLabelText(/^kuruluş adı$/i), "Örnek A.Ş.");
  await user.type(screen.getByLabelText(/e-posta/i), email);
  await user.type(screen.getByLabelText(/^şifre$/i), "SecurePass123!");
  await user.type(screen.getByLabelText(/şifre tekrar/i), "SecurePass123!");
  await user.type(screen.getByLabelText(/ad soyad/i), "Yetkili Kişi");
}

function pdf(name = "sicil.pdf", type = "application/pdf", size = 20): File {
  return new File([new Uint8Array(size)], name, { type });
}

/**
 * Kuruluş kaydı: kurumsal e-posta zorunluluğu, MERSİS alanı ve (mock) belge adımı.
 */
describe("RegisterForm — kuruluş kaydı", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as unknown as ReturnType<typeof useRouter>);
  });

  afterEach(() => {
    cleanup();
  });

  it("MERSİS ve belge alanları yalnız Kuruluş seçilince görünür", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    expect(screen.queryByLabelText(messages.kayit.mersisLabel)).toBeNull();
    expect(screen.queryByLabelText(messages.kayit.documentLabel)).toBeNull();

    await chooseOrganization(user);

    expect(screen.getByLabelText(messages.kayit.mersisLabel)).toBeTruthy();
    expect(screen.getByLabelText(messages.kayit.documentLabel)).toBeTruthy();
    expect(screen.getByText(messages.kayit.corporateEmailHint)).toBeTruthy();

    await user.click(screen.getByRole("radio", { name: /^Kurum\b(?!\/)/ }));

    expect(screen.queryByLabelText(messages.kayit.mersisLabel)).toBeNull();
  });

  it("ücretsiz e-posta ile kuruluş kaydı gönderilmez, hata e-posta alanında görünür", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);
    await chooseOrganization(user);
    await fillAccount(user, "yetkili@gmail.com");

    await user.click(screen.getByRole("button", { name: messages.kayit.submit }));

    await waitFor(() => {
      expect(screen.getByText(messages.kayit.corporateEmailRequired)).toBeTruthy();
    });
    expect(clientApi.register).not.toHaveBeenCalled();
  });

  it("16 hane olmayan MERSİS ile kayıt gönderilmez", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);
    await chooseOrganization(user);
    await fillAccount(user, "yetkili@ornek-firma.com.tr");
    await user.type(screen.getByLabelText(messages.kayit.mersisLabel), "12345");

    await user.click(screen.getByRole("button", { name: messages.kayit.submit }));

    await waitFor(() => {
      expect(screen.getByText(messages.kayit.mersisInvalid)).toBeTruthy();
    });
    expect(clientApi.register).not.toHaveBeenCalled();
  });

  it("kurumsal e-posta ve MERSİS ile kayıt: MERSİS gönderilir, kurumsal adres mesajı gösterilir", async () => {
    vi.mocked(clientApi.register).mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(<RegisterForm />);
    await chooseOrganization(user);
    await fillAccount(user, "yetkili@ornek-firma.com.tr");
    await user.type(screen.getByLabelText(messages.kayit.mersisLabel), MERSIS);

    await user.click(screen.getByRole("button", { name: messages.kayit.submit }));

    await waitFor(() => {
      expect(clientApi.register).toHaveBeenCalledWith(
        "yetkili@ornek-firma.com.tr",
        "SecurePass123!",
        "Yetkili Kişi",
        "ORGANIZATION",
        "Örnek A.Ş.",
        MERSIS
      );
    });
    expect(screen.getByRole("status").textContent).toBe(messages.kayit.successOrganization);
  });

  it("MERSİS boş bırakılırsa kayıt MERSİS'siz gönderilir", async () => {
    vi.mocked(clientApi.register).mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(<RegisterForm />);
    await chooseOrganization(user);
    await fillAccount(user, "yetkili@ornek-firma.com.tr");

    await user.click(screen.getByRole("button", { name: messages.kayit.submit }));

    await waitFor(() => {
      expect(clientApi.register).toHaveBeenCalledWith(
        "yetkili@ornek-firma.com.tr",
        "SecurePass123!",
        "Yetkili Kişi",
        "ORGANIZATION",
        "Örnek A.Ş."
      );
    });
  });

  it("sunucu 409 LEGAL_ID_TAKEN dönerse hata MERSİS alanında görünür", async () => {
    vi.mocked(clientApi.register).mockRejectedValueOnce({ status: 409, code: "LEGAL_ID_TAKEN" });
    const user = userEvent.setup();
    render(<RegisterForm />);
    await chooseOrganization(user);
    await fillAccount(user, "yetkili@ornek-firma.com.tr");
    await user.type(screen.getByLabelText(messages.kayit.mersisLabel), MERSIS);

    await user.click(screen.getByRole("button", { name: messages.kayit.submit }));

    await waitFor(() => {
      expect(screen.getByText(messages.kayit.mersisTaken)).toBeTruthy();
    });
  });

  it("sunucu ücretsiz e-postayı 422 ile reddederse alan hatası gösterilir", async () => {
    vi.mocked(clientApi.register).mockRejectedValueOnce({
      status: 422,
      fields: { email: "Kuruluş hesabı için kurumsal e-posta adresi gereklidir." },
    });
    const user = userEvent.setup();
    render(<RegisterForm />);
    await chooseOrganization(user);
    await fillAccount(user, "yetkili@listede-olmayan-ucretsiz.example");

    await user.click(screen.getByRole("button", { name: messages.kayit.submit }));

    await waitFor(() => {
      expect(screen.getByText("Kuruluş hesabı için kurumsal e-posta adresi gereklidir.")).toBeTruthy();
    });
  });

  describe("belge adımı (mock)", () => {
    it("ad ve MERSİS girilmişse 'Kayıtla eşleşiyor' ve örnek sonuç notu gösterilir", async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);
      await chooseOrganization(user);
      await user.type(screen.getByLabelText(/^kuruluş adı$/i), "Örnek A.Ş.");
      await user.type(screen.getByLabelText(messages.kayit.mersisLabel), MERSIS);
      await user.upload(screen.getByLabelText(messages.kayit.documentLabel), pdf());

      await user.click(screen.getByRole("button", { name: messages.kayit.documentCheckButton }));

      await waitFor(() => {
        expect(screen.getByText(messages.kayit.documentMatch)).toBeTruthy();
      });
      expect(screen.getByText(messages.kayit.documentQrFound)).toBeTruthy();
      expect(screen.getByText(messages.kayit.documentDemoNote)).toBeTruthy();
      expect(screen.queryByText(messages.kayit.documentManualReview)).toBeNull();
    });

    it("MERSİS yoksa 'Doğrulanamadı' ve manuel inceleme mesajı gösterilir", async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);
      await chooseOrganization(user);
      await user.type(screen.getByLabelText(/^kuruluş adı$/i), "Örnek A.Ş.");
      await user.upload(screen.getByLabelText(messages.kayit.documentLabel), pdf());

      await user.click(screen.getByRole("button", { name: messages.kayit.documentCheckButton }));

      await waitFor(() => {
        expect(screen.getByText(messages.kayit.documentUnverified)).toBeTruthy();
      });
      expect(screen.getByText(messages.kayit.documentManualReview)).toBeTruthy();
      expect(screen.getByText(messages.kayit.documentDemoNote)).toBeTruthy();
    });

    it("belge seçilmeden kontrol düğmesi pasiftir", async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);
      await chooseOrganization(user);

      const button = screen.getByRole("button", { name: messages.kayit.documentCheckButton }) as HTMLButtonElement;
      expect(button.disabled).toBe(true);
    });

    it("5 MB'den büyük dosya reddedilir ve kontrol düğmesi pasif kalır", async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);
      await chooseOrganization(user);

      await user.upload(
        screen.getByLabelText(messages.kayit.documentLabel),
        pdf("buyuk.pdf", "application/pdf", 5 * 1024 * 1024 + 1)
      );

      expect(screen.getByText(messages.kayit.documentTooLarge)).toBeTruthy();
      const button = screen.getByRole("button", { name: messages.kayit.documentCheckButton }) as HTMLButtonElement;
      expect(button.disabled).toBe(true);
    });

    it("belge kontrolü kaydı göndermez (form gönderiminden bağımsızdır)", async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);
      await chooseOrganization(user);
      await user.upload(screen.getByLabelText(messages.kayit.documentLabel), pdf());

      await user.click(screen.getByRole("button", { name: messages.kayit.documentCheckButton }));

      await waitFor(() => {
        expect(screen.getByText(messages.kayit.documentUnverified)).toBeTruthy();
      });
      expect(clientApi.register).not.toHaveBeenCalled();
    });
  });
});
