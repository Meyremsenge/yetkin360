import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthLayout } from "./auth-layout";

/**
 * ATDD — AuthLayout bileşeni testleri (fe15-auth-duzeni-sicil-gisesi)
 * Prop sözleşmesi (plan.md, sabit):
 *   brandSentence: string
 *   links?: { href: string; label: string }[]
 *   children: React.ReactNode
 */

const BRAND_SENTENCE = "Sicil kaydınız, kanıtlarınızla birlikte güvenle saklanır.";
const CHAIN_LABELS = ["Beyan", "Kanıt", "Tanıklık", "Doğrulanmış Deneyim"];

/** Verilen container içindeki, verilen class token'ını taşıyan tüm elementleri döndürür. */
function elementsWithClass(container: HTMLElement, token: string): Element[] {
  return Array.from(container.querySelectorAll("*")).filter((el) =>
    el.classList.contains(token)
  );
}

describe("AuthLayout Component", () => {
  describe("AC-1: masaüstü iki kolonlu düzen", () => {
    it("AC-1: marka panelinde wordmark 'Yetkin360' ve brandSentence metni görünmeli", () => {
      render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      expect(screen.getByText("Yetkin360")).toBeTruthy();
      expect(screen.getByText(BRAND_SENTENCE)).toBeTruthy();
    });

    it("AC-1: marka panelinde 4 adımlı zincir (Beyan/Kanıt/Tanıklık/Doğrulanmış Deneyim) görünmeli", () => {
      render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      for (const label of CHAIN_LABELS) {
        expect(screen.getByText(label)).toBeTruthy();
      }
    });

    it("AC-1: children (form içeriği) render edilmeli", () => {
      render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      expect(screen.getByText("Form içeriği")).toBeTruthy();
    });

    it("AC-1: marka paneli form içeriğinden önce (sol kolon) gelmeli", () => {
      render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      const brand = screen.getByText("Yetkin360");
      const form = screen.getByText("Form içeriği");
      // Node.DOCUMENT_POSITION_FOLLOWING (4): form, marka wordmark'ından sonra gelir.
      expect(brand.compareDocumentPosition(form) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
  });

  describe("AC-2: mobil tek kolon düzeni", () => {
    it("AC-2: sarmalayıcı grid className'inde grid-cols-1 token'ı bulunmalı", () => {
      const { container } = render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      const grids = elementsWithClass(container, "grid");
      const hasSingleColumn = grids.some((el) => el.classList.contains("grid-cols-1"));
      expect(hasSingleColumn).toBe(true);
    });
  });

  describe("AC-3: --sand token'ı marka panelinde", () => {
    it("AC-3: marka paneli className'inde tam 'bg-sand' token'ı bulunmalı", () => {
      const { container } = render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      const sandPanels = elementsWithClass(container, "bg-sand");
      expect(sandPanels.length).toBeGreaterThan(0);
    });

    it("AC-3: bg-sand token'ı taşıyan panel, wordmark'ı ve marka cümlesini içermeli", () => {
      const { container } = render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      const sandPanels = elementsWithClass(container, "bg-sand");
      const brandPanel = sandPanels.find((el) => el.textContent?.includes("Yetkin360"));
      expect(brandPanel).toBeDefined();
      expect(brandPanel?.textContent).toContain(BRAND_SENTENCE);
    });

    it("AC-3: form içeriği bg-sand token'ı taşımamalı (sadece marka paneli kum zeminli)", () => {
      const { container } = render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      const formText = screen.getByText("Form içeriği");
      const ancestorsWithSand = elementsWithClass(container, "bg-sand").filter((el) =>
        el.contains(formText)
      );
      expect(ancestorsWithSand.length).toBe(0);
    });
  });

  describe("AC-6: children içindeki aria-live korunmalı", () => {
    it("AC-6: children'daki aria-live='assertive' attribute'u DOM'da aynen korunmalı", () => {
      const { container } = render(
        <AuthLayout brandSentence={BRAND_SENTENCE}>
          <div aria-live="assertive">Hata: e-posta geçersiz</div>
        </AuthLayout>
      );
      const liveRegion = container.querySelector('[aria-live="assertive"]');
      expect(liveRegion).not.toBeNull();
      expect(liveRegion?.textContent).toBe("Hata: e-posta geçersiz");
    });
  });

  describe("AC-7: çapraz linkler", () => {
    const LINKS = [
      { href: "/kayit", label: "Kayıt Ol" },
      { href: "/sifre-unuttum", label: "Şifremi Unuttum" },
    ];

    it("AC-7: her link role=link ile erişilebilir ve adı label'a eşit olmalı", () => {
      render(
        <AuthLayout brandSentence={BRAND_SENTENCE} links={LINKS}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      expect(screen.getByRole("link", { name: "Kayıt Ol" })).toBeTruthy();
      expect(screen.getByRole("link", { name: "Şifremi Unuttum" })).toBeTruthy();
    });

    it("AC-7: her link href'i verilen değere birebir eşit olmalı", () => {
      render(
        <AuthLayout brandSentence={BRAND_SENTENCE} links={LINKS}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      expect(screen.getByRole("link", { name: "Kayıt Ol" }).getAttribute("href")).toBe("/kayit");
      expect(
        screen.getByRole("link", { name: "Şifremi Unuttum" }).getAttribute("href")
      ).toBe("/sifre-unuttum");
    });

    it("AC-7: links prop'u verilmezse hiçbir link render edilmemeli ve crash olmamalı", () => {
      expect(() =>
        render(
          <AuthLayout brandSentence={BRAND_SENTENCE}>
            <p>Form içeriği</p>
          </AuthLayout>
        )
      ).not.toThrow();
      expect(screen.queryAllByRole("link")).toHaveLength(0);
    });

    it("AC-7: links boş dizi verilirse hiçbir link render edilmemeli", () => {
      render(
        <AuthLayout brandSentence={BRAND_SENTENCE} links={[]}>
          <p>Form içeriği</p>
        </AuthLayout>
      );
      expect(screen.queryAllByRole("link")).toHaveLength(0);
    });
  });

  describe("AC-8: children yokken crash olmamalı", () => {
    it("AC-8: children undefined iken render hata fırlatmamalı ve marka paneli görünmeli", () => {
      expect(() =>
        render(<AuthLayout brandSentence={BRAND_SENTENCE}>{undefined}</AuthLayout>)
      ).not.toThrow();
      expect(screen.getByText("Yetkin360")).toBeTruthy();
    });
  });
});
