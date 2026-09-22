import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import NotFound from "@/app/not-found";
import messages from "@/messages/tr.json";

/**
 * AC-6: not-found.tsx — 404 + bağlantılar.
 * Davranış Sözleşmesi satır 3: Var olmayan rota.
 */

describe("NotFound (not-found.tsx)", () => {
  describe("AC-6: 404 sayfası", () => {
    it("AC-6: başlık messages.notFound.title metni içerir", () => {
      render(<NotFound />);
      const heading = screen.getByRole("heading");
      expect(heading.textContent).toContain(messages.notFound.title);
    });

    it("AC-6: başlık vardır", () => {
      render(<NotFound />);
      const heading = screen.getByRole("heading");
      expect(heading).toBeTruthy();
    });

    it("AC-6: ana sayfa bağlantısı href='/'", () => {
      render(<NotFound />);
      const homeLink = screen.getByRole("link", {
        name: messages.notFound.home,
      });
      expect(homeLink.getAttribute("href")).toBe("/");
    });

    it("AC-6: giriş bağlantısı href='/giris'", () => {
      render(<NotFound />);
      const loginLink = screen.getByRole("link", {
        name: messages.notFound.login,
      });
      expect(loginLink.getAttribute("href")).toBe("/giris");
    });

    it("AC-6: iki link beraber render edilir", () => {
      render(<NotFound />);
      expect(
        screen.getByRole("link", { name: messages.notFound.home })
      ).toBeTruthy();
      expect(
        screen.getByRole("link", { name: messages.notFound.login })
      ).toBeTruthy();
    });
  });

  describe("AC-6: Metin içeriği", () => {
    it("AC-6: messages.notFound.title metni gözükür", () => {
      render(<NotFound />);
      expect(screen.getByText(messages.notFound.title)).toBeTruthy();
    });

    it("AC-6: messages.notFound.home bağlantı metni", () => {
      render(<NotFound />);
      expect(
        screen.getByRole("link", { name: messages.notFound.home })
      ).toBeTruthy();
    });

    it("AC-6: messages.notFound.login bağlantı metni", () => {
      render(<NotFound />);
      expect(
        screen.getByRole("link", { name: messages.notFound.login })
      ).toBeTruthy();
    });
  });

  describe("Davranış Sözleşmesi satır 3: Var olmayan rota", () => {
    it("Davranış 3: not-found → 404 sayfası render edilir", () => {
      render(<NotFound />);
      expect(
        screen.getByRole("heading", { name: messages.notFound.title })
      ).toBeTruthy();
    });

    it("Davranış 3: başlığa ek olarak navigasyon bağlantıları", () => {
      render(<NotFound />);
      expect(
        screen.getByRole("link", { name: messages.notFound.home })
      ).toBeTruthy();
      expect(
        screen.getByRole("link", { name: messages.notFound.login })
      ).toBeTruthy();
    });
  });
});
