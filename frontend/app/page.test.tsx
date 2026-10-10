import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Home from "./page";
import messages from "@/messages/tr.json";

/**
 * ATDD — Landing sayfası (/) bütünlük testleri (fe12-landing-sicil-gazetesi)
 * Varsayımlar: header/main/footer semantik elemanları; hero grid'i "grid-cols-1" token'ı taşır;
 * rakamlar şeridi "stats-strip" test-id'si ile işaretlenir (veri yokken DOM'a girmez).
 */

describe("Home (Landing) Page", () => {
  describe("AC-1: bölüm sırası ve varlığı", () => {
    it("AC-1: üst bar (header) DOM'da bulunmalı", () => {
      const { container } = render(<Home />);
      expect(container.querySelector("header")).not.toBeNull();
    });

    it("AC-1: hero başlığı (h1) DOM'da bulunmalı", () => {
      const { container } = render(<Home />);
      expect(container.querySelector("h1")).not.toBeNull();
    });

    it("AC-1: ChainProgress zincir adımları (Beyan, Kanıt, Tanıklık, Doğrulanmış Deneyim) DOM'da bulunmalı", () => {
      render(<Home />);
      expect(screen.getByText("Beyan")).toBeTruthy();
      expect(screen.getByText("Kanıt")).toBeTruthy();
      expect(screen.getByText("Tanıklık")).toBeTruthy();
      expect(screen.getByText("Doğrulanmış Deneyim")).toBeTruthy();
    });

    it("AC-1: 3 persona kartı ('Bireysel', 'Kuruluş', 'Kurum') DOM'da bulunmalı", () => {
      render(<Home />);
      expect(screen.getByText("Bireysel")).toBeTruthy();
      expect(screen.getByText("Kuruluş")).toBeTruthy();
      expect(screen.getByText("Kurum")).toBeTruthy();
    });

    it("AC-1: footer DOM'da bulunmalı", () => {
      const { container } = render(<Home />);
      expect(container.querySelector("footer")).not.toBeNull();
    });

    it("AC-1: bölümler sırayla render edilmeli (header < h1 < ChainProgress < persona < footer)", () => {
      const { container } = render(<Home />);
      const header = container.querySelector("header");
      const h1 = container.querySelector("h1");
      const chainStart = screen.getByText("Beyan");
      const persona = screen.getByText("Bireysel");
      const footer = container.querySelector("footer");

      expect(header).not.toBeNull();
      expect(h1).not.toBeNull();
      expect(footer).not.toBeNull();

      // DOCUMENT_POSITION_FOLLOWING (4) => ikinci eleman birincinin sonrasında gelir
      const follows = (a: Element, b: Element) =>
        (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;

      expect(follows(header!, h1!)).toBe(true);
      expect(follows(h1!, chainStart)).toBe(true);
      expect(follows(chainStart, persona)).toBe(true);
      expect(follows(persona, footer!)).toBe(true);
    });
  });

  describe("AC-2: CTA link hedefleri (tam href eşleşmesi)", () => {
    it("AC-2: 'Kayıt Ol' link(ler)i href='/kayit' olmalı", () => {
      render(<Home />);
      const links = screen.getAllByRole("link", { name: "Kayıt Ol" });
      expect(links.length).toBeGreaterThan(0);
      for (const link of links) {
        expect(link.getAttribute("href")).toBe("/kayit");
      }
    });

    it("AC-2: 'Giriş Yap' link(ler)i href='/giris' olmalı", () => {
      render(<Home />);
      const links = screen.getAllByRole("link", { name: "Giriş Yap" });
      expect(links.length).toBeGreaterThan(0);
      for (const link of links) {
        expect(link.getAttribute("href")).toBe("/giris");
      }
    });

    // The sample-verification CTA scrolls to the live sample record on the page.
    it("AC-2: 'Örnek Bir Doğrulamayı İncele' linki href='#zincir' olmalı", () => {
      render(<Home />);
      const links = screen.getAllByRole("link", { name: "Örnek Bir Doğrulamayı İncele" });
      expect(links.length).toBeGreaterThan(0);
      for (const link of links) {
        expect(link.getAttribute("href")).toBe("#zincir");
      }
    });
  });

  describe("AC-3: rakamlar şeridi — veri yoksa DOM'a hiç girmemeli", () => {
    it("AC-3: data-testid='stats-strip' DOM'da bulunmamalı", () => {
      render(<Home />);
      expect(screen.queryByTestId("stats-strip")).toBeNull();
    });

    it("AC-3: rakamlar şeridi başlığı ('Rakamlarla') DOM'da bulunmamalı", () => {
      render(<Home />);
      expect(screen.queryByText(/Rakamlarla/i)).toBeNull();
    });
  });

  describe("AC-4 / Davranış 3: mobil hero — tek sütun ve sıralama", () => {
    it("AC-4: hero grid'i 'grid-cols-1' token'ı ile tek sütunla başlamalı", () => {
      const { container } = render(<Home />);
      const h1 = container.querySelector("h1");
      const hero = h1?.closest("section");
      expect(hero).not.toBeNull();
      expect(Array.from(hero!.classList)).toContain("grid-cols-1");
    });

    it("AC-4: DOM sırası: başlık (h1) sertifika kartından (VerifiedSeal) ÖNCE gelmeli", () => {
      const { container } = render(<Home />);
      const h1 = container.querySelector("h1");
      const seal = container.querySelector("[data-testid='verified-seal']");
      expect(h1).not.toBeNull();
      expect(seal).not.toBeNull();
      const headingBeforeSeal =
        (h1!.compareDocumentPosition(seal!) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
      expect(headingBeforeSeal).toBe(true);
    });
  });

  describe("AC-8: metinler messages/tr.json üzerinden gelmeli", () => {
    it("AC-8: sayfa messages.home.title değerini içermeli", () => {
      render(<Home />);
      expect(screen.getAllByText(messages.home.title).length).toBeGreaterThan(0);
    });

    it("AC-8: sayfa messages.home.tagline değerini içermeli", () => {
      render(<Home />);
      expect(screen.getAllByText(messages.home.tagline).length).toBeGreaterThan(0);
    });
  });
});
