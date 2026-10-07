import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "./card";

/**
 * ATDD — Card bileşeni testleri
 * AC-8: Card bileşeni — tek tip, className override desteği
 */

describe("Card Component", () => {
  describe("AC-8: Card render'lanması ve temel class'lar", () => {
    it("AC-8: <Card>İçerik</Card> render edildiğinde children bulunmalı", () => {
      render(<Card>İçerik</Card>);
      expect(screen.getByText("İçerik")).toBeTruthy();
    });

    it("AC-8: <Card> className'de bg-card BULUNMALI", () => {
      const { container } = render(<Card>Test</Card>);
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("bg-card");
    });

    it("AC-8: <Card> className'de text-foreground BULUNMALI", () => {
      const { container } = render(<Card>Test</Card>);
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("text-foreground");
    });

    it("AC-8: <Card> className'de border BULUNMALI (margin/padding için)", () => {
      const { container } = render(<Card>Test</Card>);
      const wrapper = container.querySelector("div");
      // `border` class'ı CSS'te border'ı açar
      expect(wrapper?.className).toContain("border");
    });

    it("AC-8: <Card> className'de border-border BULUNMALI", () => {
      const { container } = render(<Card>Test</Card>);
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("border-border");
    });

    it("AC-8: <Card> className'de rounded-lg BULUNMALI", () => {
      const { container } = render(<Card>Test</Card>);
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("rounded-lg");
    });

    it("AC-8: <Card> className'de p-6 BULUNMALI (iç padding)", () => {
      const { container } = render(<Card>Test</Card>);
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("p-6");
    });
  });

  describe("AC-8: Card className override desteği", () => {
    it("AC-8: <Card className='custom-class'> className'de custom-class BULUNMALI", () => {
      const { container } = render(
        <Card className="custom-class">İçerik</Card>
      );
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("custom-class");
    });

    it("AC-8: <Card className='custom-class'> hala temel class'ları içerir — bg-card", () => {
      const { container } = render(
        <Card className="custom-class">İçerik</Card>
      );
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("bg-card");
    });

    it("AC-8: <Card className='custom-class'> hala border'ı içerir", () => {
      const { container } = render(
        <Card className="custom-class">İçerik</Card>
      );
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("border");
    });

    it("AC-8: <Card className='p-4'> (override: p-6 yerine p-4) className'de p-4 BULUNMALI", () => {
      const { container } = render(
        <Card className="p-4">İçerik</Card>
      );
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("p-4");
    });

    it("AC-8: <Card className='p-4'> (override: p-6 yerine p-4) className'de p-6 BULUNMAMALI", () => {
      const { container } = render(
        <Card className="p-4">İçerik</Card>
      );
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).not.toContain("p-6");
    });

    it("AC-8: <Card className='shadow-lg'> className'de shadow-lg BULUNMALI", () => {
      const { container } = render(
        <Card className="shadow-lg">İçerik</Card>
      );
      const wrapper = container.querySelector("div");
      expect(wrapper?.className).toContain("shadow-lg");
    });
  });

  describe("AC-8: Card iç içe geçebilmesi (bileşim)", () => {
    it("AC-8: <Card><Card>İç Card</Card></Card> her ikisi de render edilmeli", () => {
      render(
        <Card>
          Dış Card
          <Card>İç Card</Card>
        </Card>
      );
      expect(screen.getByText("Dış Card")).toBeTruthy();
      expect(screen.getByText("İç Card")).toBeTruthy();
    });

    it("AC-8: İç Card'ın className'de de bg-card BULUNMALI", () => {
      const { container } = render(
        <Card>
          <Card>İç Card</Card>
        </Card>
      );
      // En az 2 div bulunmalı (dış + iç Card), her ikisinin de bg-card'ı olmalı
      const cards = container.querySelectorAll("div[class*='bg-card']");
      expect(cards.length).toBeGreaterThanOrEqual(2);
    });
  });
});
