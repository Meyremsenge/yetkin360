import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChainProgress } from "./chain-progress";

/**
 * ATDD — ChainProgress bileşeni testleri (fe12-landing-sicil-gazetesi)
 * Prop sözleşmesi (varsayım): steps: { label: string; completed: boolean }[]
 * Yalnızca son adım (Doğrulanmış Deneyim) completed=true iken çam yeşili vurgulanır.
 */

const CHAIN_STEPS = [
  { label: "Beyan", completed: false },
  { label: "Kanıt", completed: false },
  { label: "Tanıklık", completed: false },
  { label: "Doğrulanmış Deneyim", completed: true },
];

/** Verilen elemanın ve üst zincirinin (container'a kadar) class token'larını toplar. */
function classTokensUpTo(el: Element, root: Element): string[] {
  const tokens: string[] = [];
  let current: Element | null = el;
  while (current && current !== root.parentElement) {
    tokens.push(...Array.from(current.classList));
    if (current === root) break;
    current = current.parentElement;
  }
  return tokens;
}

describe("ChainProgress Component", () => {
  describe("AC-5: boş status listesi — crash olmamalı", () => {
    it("AC-5: steps={[]} ile render edildiğinde hata fırlatmamalı", () => {
      expect(() => render(<ChainProgress steps={[]} />)).not.toThrow();
    });

    it("AC-5: steps={[]} ile hiçbir zincir adımı metni görünmemeli", () => {
      render(<ChainProgress steps={[]} />);
      expect(screen.queryByText("Beyan")).toBeNull();
      expect(screen.queryByText("Kanıt")).toBeNull();
      expect(screen.queryByText("Tanıklık")).toBeNull();
      expect(screen.queryByText("Doğrulanmış Deneyim")).toBeNull();
    });
  });

  describe("AC-1 / Davranış 1: dolu 4 adımlı zincir", () => {
    it("AC-1: Beyan, Kanıt, Tanıklık ve Doğrulanmış Deneyim adımlarının metinleri görünmeli", () => {
      render(<ChainProgress steps={CHAIN_STEPS} />);
      expect(screen.getByText("Beyan")).toBeTruthy();
      expect(screen.getByText("Kanıt")).toBeTruthy();
      expect(screen.getByText("Tanıklık")).toBeTruthy();
      expect(screen.getByText("Doğrulanmış Deneyim")).toBeTruthy();
    });

    it("AC-1: Doğrulanmış Deneyim (tamamlanan son adım) className'de bg-success veya text-success token'ı içermeli", () => {
      const { container } = render(<ChainProgress steps={CHAIN_STEPS} />);
      const finalStep = screen.getByText("Doğrulanmış Deneyim");
      const tokens = classTokensUpTo(finalStep, container);
      const hasSuccess = tokens.includes("bg-success") || tokens.includes("text-success");
      expect(hasSuccess).toBe(true);
    });

    it("AC-1: Beyan adımı (tamamlanmamış) className'de bg-success veya text-success İÇERMEMELİ", () => {
      const { container } = render(<ChainProgress steps={CHAIN_STEPS} />);
      const step = screen.getByText("Beyan");
      const tokens = classTokensUpTo(step, container);
      expect(tokens.includes("bg-success")).toBe(false);
      expect(tokens.includes("text-success")).toBe(false);
    });

    it("AC-1: Kanıt adımı className'de bg-success veya text-success İÇERMEMELİ", () => {
      const { container } = render(<ChainProgress steps={CHAIN_STEPS} />);
      const step = screen.getByText("Kanıt");
      const tokens = classTokensUpTo(step, container);
      expect(tokens.includes("bg-success")).toBe(false);
      expect(tokens.includes("text-success")).toBe(false);
    });

    it("AC-1: Tanıklık adımı className'de bg-success veya text-success İÇERMEMELİ", () => {
      const { container } = render(<ChainProgress steps={CHAIN_STEPS} />);
      const step = screen.getByText("Tanıklık");
      const tokens = classTokensUpTo(step, container);
      expect(tokens.includes("bg-success")).toBe(false);
      expect(tokens.includes("text-success")).toBe(false);
    });
  });

  describe("AC-7 / Davranış 6: prefers-reduced-motion", () => {
    it("AC-7: render çıktısında en az bir element motion-reduce: Tailwind prefix'li class taşımalı", () => {
      const { container } = render(<ChainProgress steps={CHAIN_STEPS} />);
      const allElements = Array.from(container.querySelectorAll("*"));
      const hasMotionReduce = allElements.some((el) =>
        Array.from(el.classList).some((token) => token.startsWith("motion-reduce:"))
      );
      expect(hasMotionReduce).toBe(true);
    });

    it("AC-7: motion-reduce: token'ı animasyon/geçiş class'ı ile birlikte kullanılmalı (transition veya animate)", () => {
      const { container } = render(<ChainProgress steps={CHAIN_STEPS} />);
      const allTokens = Array.from(container.querySelectorAll("*")).flatMap((el) =>
        Array.from(el.classList)
      );
      const motionReduceTokens = allTokens.filter((t) => t.startsWith("motion-reduce:"));
      const hasMotionDisable = motionReduceTokens.some(
        (t) => t.includes("transition") || t.includes("animate")
      );
      expect(hasMotionDisable).toBe(true);
    });
  });
});
