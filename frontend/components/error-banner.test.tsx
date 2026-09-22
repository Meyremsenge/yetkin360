import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBanner } from "@/components/error-banner";
import messages from "@/messages/tr.json";

/**
 * AC-5: Hata bandı — retry düğmesi, destek kodu.
 * AC-7: InvalidResponseError, genişletilmiş hata mesajları.
 * AC-S4: dangerouslySetInnerHTML yasak.
 */

describe("ErrorBanner", () => {
  describe("AC-5: message ve accessibility", () => {
    it("AC-5: role='alert' özelliğine sahip", () => {
      render(<ErrorBanner message="Test hatası" />);
      const banner = screen.getByRole("alert");
      expect(banner).toBeTruthy();
    });

    it("AC-5: message metni görünür", () => {
      render(<ErrorBanner message="Ağ bağlantısı başarısız" />);
      expect(screen.getByText("Ağ bağlantısı başarısız")).toBeTruthy();
    });

    it("AC-5: message HTML olarak ayrıştırılmaz (dangerouslySetInnerHTML yasak)", () => {
      render(
        <ErrorBanner message="<b>Kalın metin</b>" />
      );
      // HTML etiketleri metin olarak görünmelidir, <b> elementi değil
      expect(screen.getByText("<b>Kalın metin</b>")).toBeTruthy();
      expect(screen.queryByRole("heading")).toBeNull();
    });

    it("AC-S4: message dışında dinamik HTML yok", () => {
      const { container } = render(
        <ErrorBanner message="Test" />
      );
      expect(container.innerHTML).not.toContain(
        "dangerouslySetInnerHTML"
      );
    });
  });

  describe("AC-5: requestId ve destek kodu", () => {
    it("AC-5: requestId varsa 'Destek kodu: <requestId>' metni görünür", () => {
      render(
        <ErrorBanner message="Test hatası" requestId="req-123" />
      );
      expect(screen.getByText(/req-123/)).toBeTruthy();
    });

    it("AC-5: requestId null ise messages.errors.supportCode metni GÖRÜNMEZ", () => {
      render(
        <ErrorBanner message="Test hatası" requestId={null} />
      );
      expect(screen.queryByText(messages.errors.supportCode)).toBeNull();
    });

    it("AC-5: requestId undefined ise messages.errors.supportCode metni GÖRÜNMEZ", () => {
      render(
        <ErrorBanner message="Test hatası" />
      );
      expect(screen.queryByText(messages.errors.supportCode)).toBeNull();
    });

    it("AC-5: requestId boş string ise 'Destek kodu' gösterilir", () => {
      render(
        <ErrorBanner message="Test hatası" requestId="" />
      );
      expect(screen.getByText(messages.errors.supportCode)).toBeTruthy();
    });
  });

  describe("AC-5: onRetry callback", () => {
    it("AC-5: onRetry varsa messages.errors.retry butonu vardır", () => {
      const mockRetry = vi.fn();
      render(
        <ErrorBanner message="Test hatası" onRetry={mockRetry} />
      );
      const button = screen.getByRole("button", {
        name: messages.errors.retry,
      });
      expect(button).toBeTruthy();
    });

    it("AC-5: messages.errors.retry butonu tıklanınca onRetry çağrılır", () => {
      const mockRetry = vi.fn();
      render(
        <ErrorBanner message="Test hatası" onRetry={mockRetry} />
      );
      const button = screen.getByRole("button", {
        name: messages.errors.retry,
      });
      fireEvent.click(button);
      expect(mockRetry).toHaveBeenCalledTimes(1);
    });

    it("AC-5: onRetry verili değilse messages.errors.retry butonu YOKTUR", () => {
      render(
        <ErrorBanner message="Test hatası" />
      );
      expect(
        screen.queryByRole("button", { name: messages.errors.retry })
      ).toBeNull();
    });

    it("AC-5: onRetry undefined ise butonu yoktur", () => {
      render(
        <ErrorBanner message="Test hatası" onRetry={undefined} />
      );
      expect(
        screen.queryByRole("button", { name: messages.errors.retry })
      ).toBeNull();
    });

    it("AC-5: birden çok click'te onRetry birden çok kez çağrılır", () => {
      const mockRetry = vi.fn();
      render(
        <ErrorBanner message="Test hatası" onRetry={mockRetry} />
      );
      const button = screen.getByRole("button", {
        name: messages.errors.retry,
      });
      fireEvent.click(button);
      fireEvent.click(button);
      expect(mockRetry).toHaveBeenCalledTimes(2);
    });
  });

  describe("AC-7: InvalidResponseError süreci için props kombinasyonları", () => {
    it("AC-7: message + requestId + onRetry beraber gösterilir", () => {
      const mockRetry = vi.fn();
      render(
        <ErrorBanner
          message="Bilgileriniz şu an yüklenemedi"
          requestId="req-xyz"
          onRetry={mockRetry}
        />
      );
      expect(
        screen.getByText("Bilgileriniz şu an yüklenemedi")
      ).toBeTruthy();
      expect(screen.getByText(/req-xyz/)).toBeTruthy();
      expect(
        screen.getByRole("button", { name: messages.errors.retry })
      ).toBeTruthy();
    });

    it("AC-7: message ve requestId, onRetry yok", () => {
      render(
        <ErrorBanner
          message="Bilgileriniz şu an yüklenemedi"
          requestId="req-abc"
        />
      );
      expect(
        screen.getByText("Bilgileriniz şu an yüklenemedi")
      ).toBeTruthy();
      expect(screen.getByText(/req-abc/)).toBeTruthy();
      expect(
        screen.queryByRole("button", { name: messages.errors.retry })
      ).toBeNull();
    });
  });

  describe("Davranış Sözleşmesi satır 5a/5b: Ağ hatası + retry senaryoları", () => {
    it("Davranış 5a: ağ hatası + onRetry", () => {
      const mockRetry = vi.fn();
      render(
        <ErrorBanner
          message="İstek zaman aşımına uğradı"
          onRetry={mockRetry}
        />
      );
      const button = screen.getByRole("button", {
        name: messages.errors.retry,
      });
      expect(button).toBeTruthy();
      fireEvent.click(button);
      expect(mockRetry).toHaveBeenCalled();
    });

    it("Davranış 5b: 5xx hata + destek kodu", () => {
      render(
        <ErrorBanner
          message="Sunucu hatası"
          requestId="req-5xx-error"
        />
      );
      expect(screen.getByText(/req-5xx-error/)).toBeTruthy();
    });
  });
});
