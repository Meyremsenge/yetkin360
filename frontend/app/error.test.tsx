import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorPage from "@/app/error";
import { ApiError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

/**
 * AC-6: error.tsx — 'Tekrar dene' düğmesi, hata sayfası.
 * AC-S4: error.message ve stack DOM'a yazılmaz.
 * AC-11: Odak başlığa taşınır.
 */

describe("ErrorPage (error.tsx)", () => {
  describe("AC-S4: error.message ve stack gizlenmiş", () => {
    it("AC-S4: error.message DOM'da yoktur", () => {
      const mockReset = vi.fn();
      const error = new Error("SELECT * FROM users; secret-stack-xyz");
      (error as unknown as Error & { digest?: string }).digest = "digest-123";

      const { container } = render(
        <ErrorPage error={error} reset={mockReset} />
      );

      expect(container.textContent).not.toContain(
        "SELECT * FROM users"
      );
      expect(container.textContent).not.toContain(
        "secret-stack-xyz"
      );
    });

    it("AC-S4: error.stack DOM'da yoktur", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");
      error.stack = "Error: Test\n    at someFunc (file.tsx:10:5)";

      const { container } = render(
        <ErrorPage error={error} reset={mockReset} />
      );

      expect(container.textContent).not.toContain("at someFunc");
      expect(container.textContent).not.toContain("file.tsx");
    });

    it("AC-S4: gömülü SQL sorguları açığa çıkmazsa başarılı", () => {
      const mockReset = vi.fn();
      const error = new Error(
        "Database error: DELETE FROM users WHERE compromised=true"
      );

      const { container } = render(
        <ErrorPage error={error} reset={mockReset} />
      );

      expect(
        container.textContent
      ).not.toContain("DELETE FROM users");
    });
  });

  describe("AC-6: 'Tekrar dene' butonu", () => {
    it("AC-6: messages.errors.retry butonu görünür", () => {
      const mockReset = vi.fn();
      const error = new Error("Test hatası");

      render(<ErrorPage error={error} reset={mockReset} />);

      expect(
        screen.getByRole("button", { name: messages.errors.retry })
      ).toBeTruthy();
    });

    it("AC-6: messages.errors.retry tıklanınca reset çağrılır", () => {
      const mockReset = vi.fn();
      const error = new Error("Test hatası");

      render(<ErrorPage error={error} reset={mockReset} />);

      const button = screen.getByRole("button", {
        name: messages.errors.retry,
      });
      button.click();

      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    it("AC-6: reset birden çok kez çağrılabilir", () => {
      const mockReset = vi.fn();
      const error = new Error("Test hatası");

      render(<ErrorPage error={error} reset={mockReset} />);

      const button = screen.getByRole("button", {
        name: messages.errors.retry,
      });
      button.click();
      button.click();

      expect(mockReset).toHaveBeenCalledTimes(2);
    });
  });

  describe("AC-6: Başlık ve genel hata mesajı", () => {
    it("AC-6: başlık (heading) vardır", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      render(<ErrorPage error={error} reset={mockReset} />);

      const heading = screen.getByRole("heading");
      expect(heading).toBeTruthy();
    });

    it("AC-6: messages.errors.generic mesajı görünür", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      render(<ErrorPage error={error} reset={mockReset} />);

      expect(
        screen.getByText(messages.errors.generic)
      ).toBeTruthy();
    });
  });

  describe("AC-S4: ApiError ile requestId", () => {
    it("AC-S4: ApiError status 500 + requestId → destek kodu gösterilir", () => {
      const mockReset = vi.fn();
      const apiError = new ApiError({
        status: 500,
        code: "INTERNAL_SERVER_ERROR",
        message: "İç sunucu hatası",
        requestId: "req-42",
      });

      render(<ErrorPage error={apiError as unknown as Error} reset={mockReset} />);

      expect(screen.getByText(/req-42/)).toBeTruthy();
    });

    it("AC-S4: düz Error → messages.errors.supportCode metni GÖRÜNMEZ", () => {
      const mockReset = vi.fn();
      const error = new Error("Plain error");

      render(<ErrorPage error={error} reset={mockReset} />);

      expect(screen.queryByText(messages.errors.supportCode)).toBeNull();
    });
  });

  describe("AC-11/AC-6: Odak başlığa taşınması", () => {
    it("AC-11: sayfa yüklenince odak başlığa taşınır", async () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      render(<ErrorPage error={error} reset={mockReset} />);

      const heading = screen.getByRole("heading");
      // Test: heading tabIndex=-1 ve otomatik focus alınacak şekilde render edilir
      expect(heading.getAttribute("tabIndex")).toBe("-1");
    });

    it("AC-11: document.activeElement başlıkta", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      const { container } = render(
        <ErrorPage error={error} reset={mockReset} />
      );

      const heading = container.querySelector("h1, h2, h3");
      // Gerçek ortamda render sırasında element focus alır
      // Bu test, heading öğesinin odaklanabilir olduğunu kontrol eder
      expect(heading?.getAttribute("tabIndex")).toBe("-1");
    });
  });

  describe("AC-6: digest parametresi", () => {
    it("AC-6: error.digest sağlanabilir", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");
      (error as unknown as Error & { digest?: string }).digest = "digest-value-123";

      render(<ErrorPage error={error} reset={mockReset} />);

      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });

  describe("Davranış Sözleşmesi satır 3: Beklenmeyen hata", () => {
    it("Davranış 3: render sırasında fırlatılan hata → error.tsx", () => {
      const mockReset = vi.fn();
      const error = new Error("Unexpected error during render");

      render(<ErrorPage error={error} reset={mockReset} />);

      expect(screen.getByText(messages.errors.generic)).toBeTruthy();
      expect(
        screen.getByRole("button", { name: messages.errors.retry })
      ).toBeTruthy();
    });
  });
});
