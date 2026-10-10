import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Button } from "./button";

/**
 * ATDD — Button bileşeni testleri
 * AC-1: Varsayılan variant ve variant="primary" aynı (geriye dönük uyumluluk)
 * AC-2: variant="destructive" → bg-destructive içerir
 * AC-3: variant="secondary"/"ghost" → sırasıyla bg-muted / bg-transparent içerir
 * AC-4: size prop'ları — sm: h-8, lg: h-12, varsayılan: mevcut boyut
 * AC-5: KRİTİK — className + variant → className kazanır (tailwind-merge)
 * AC-9: Mevcut çağıranlar (hardcoded bg-red-600 gibi) regresyon görmez
 */

describe("Button Component", () => {
  describe("AC-1: Varsayılan variant (geriye dönük uyumluluk)", () => {
    it("AC-1: <Button> render edildiğinde bg-success BULUNMALI", () => {
      const { container } = render(<Button>Tıkla</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-success");
    });

    it("AC-1: <Button> render edildiğinde text-white BULUNMALI", () => {
      const { container } = render(<Button>Tıkla</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("text-white");
    });

    it("AC-1: <Button> render edildiğinde hover:bg-success/90 BULUNMALI", () => {
      const { container } = render(<Button>Tıkla</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("hover:bg-success/90");
    });

    it("AC-1: <Button variant='primary'> render edildiğinde bg-success BULUNMALI", () => {
      const { container } = render(
        <Button variant="primary">
          Tıkla
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-success");
    });

    it("AC-1: <Button variant='primary'> render edildiğinde text-white BULUNMALI", () => {
      const { container } = render(
        <Button variant="primary">
          Tıkla
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("text-white");
    });

    it("AC-1: <Button variant='primary'> render edildiğinde hover:bg-success/90 BULUNMALI", () => {
      const { container } = render(
        <Button variant="primary">
          Tıkla
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("hover:bg-success/90");
    });
  });

  describe("AC-2: variant='destructive' → bg-destructive", () => {
    it("AC-2: <Button variant='destructive'> className'de bg-destructive BULUNMALI", () => {
      const { container } = render(
        <Button variant="destructive">
          Sil
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-destructive");
    });

    it("AC-2: <Button variant='destructive'> className'de text-white BULUNMALI", () => {
      const { container } = render(
        <Button variant="destructive">
          Sil
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("text-white");
    });

    it("AC-2: <Button variant='destructive'> className'de hover:bg-destructive/90 BULUNMALI", () => {
      const { container } = render(
        <Button variant="destructive">
          Sil
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("hover:bg-destructive/90");
    });

    it("AC-2: <Button variant='destructive'> className'de bg-success BULUNMAMALI", () => {
      const { container } = render(
        <Button variant="destructive">
          Sil
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).not.toContain("bg-success");
    });
  });

  describe("AC-3: variant='secondary'/'ghost' → bg-muted / bg-transparent", () => {
    it("AC-3: <Button variant='secondary'> className'de bg-muted BULUNMALI", () => {
      const { container } = render(
        <Button variant="secondary">
          İptal
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-muted");
    });

    it("AC-3: <Button variant='secondary'> className'de text-foreground BULUNMALI", () => {
      const { container } = render(
        <Button variant="secondary">
          İptal
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("text-foreground");
    });

    it("AC-3: <Button variant='secondary'> className'de hover:bg-muted/80 BULUNMALI", () => {
      const { container } = render(
        <Button variant="secondary">
          İptal
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("hover:bg-muted/80");
    });

    it("AC-3: <Button variant='ghost'> className'de bg-transparent BULUNMALI", () => {
      const { container } = render(
        <Button variant="ghost">
          Göster
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-transparent");
    });

    it("AC-3: <Button variant='ghost'> className'de hover:bg-muted BULUNMALI", () => {
      const { container } = render(
        <Button variant="ghost">
          Göster
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("hover:bg-muted");
    });
  });

  describe("AC-4: size prop'ları — sm/md/lg", () => {
    it("AC-4: <Button size='sm'> className'de h-8 BULUNMALI", () => {
      const { container } = render(
        <Button size="sm">
          Küçük
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("h-8");
    });

    it("AC-4: <Button size='sm'> className'de px-3 BULUNMALI", () => {
      const { container } = render(
        <Button size="sm">
          Küçük
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("px-3");
    });

    it("AC-4: <Button size='sm'> className'de text-sm BULUNMALI", () => {
      const { container } = render(
        <Button size="sm">
          Küçük
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("text-sm");
    });

    it("AC-4: <Button size='lg'> className'de h-12 BULUNMALI", () => {
      const { container } = render(
        <Button size="lg">
          Büyük
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("h-12");
    });

    it("AC-4: <Button size='lg'> className'de px-6 BULUNMALI", () => {
      const { container } = render(
        <Button size="lg">
          Büyük
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("px-6");
    });

    it("AC-4: <Button size='lg'> className'de text-base BULUNMALI", () => {
      const { container } = render(
        <Button size="lg">
          Büyük
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("text-base");
    });

    it("AC-4: <Button> (size verilmez) mevcut varsayılan boyutu korur — px-4 BULUNMALI", () => {
      const { container } = render(<Button>Orta</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("px-4");
    });

    it("AC-4: <Button> (size verilmez) mevcut varsayılan boyutu korur — py-2 BULUNMALI", () => {
      const { container } = render(<Button>Orta</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("py-2");
    });
  });

  describe("AC-5: KRİTİK — className override (tailwind-merge çakışma çözümü)", () => {
    it("AC-5: <Button variant='destructive' className='bg-purple-500'> className'de bg-purple-500 BULUNMALI", () => {
      const { container } = render(
        <Button variant="destructive" className="bg-purple-500">
          Özel Renk
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-purple-500");
    });

    it("AC-5: <Button variant='destructive' className='bg-purple-500'> className'de bg-destructive BULUNMAMALI", () => {
      const { container } = render(
        <Button variant="destructive" className="bg-purple-500">
          Özel Renk
        </Button>
      );
      const btn = container.querySelector("button");
      const classTokens = btn?.className.split(" ") ?? [];
      expect(classTokens).not.toContain("bg-destructive");
    });

    it("AC-5: <Button variant='primary' className='hover:bg-red-700'> className'de hover:bg-red-700 BULUNMALI", () => {
      const { container } = render(
        <Button variant="primary" className="hover:bg-red-700">
          Hover Özel
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("hover:bg-red-700");
    });

    it("AC-5: <Button variant='primary' className='hover:bg-red-700'> className'de hover:bg-success/90 BULUNMAMALI", () => {
      const { container } = render(
        <Button variant="primary" className="hover:bg-red-700">
          Hover Özel
        </Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).not.toContain("hover:bg-success/90");
    });
  });

  describe("AC-9: Mevcut çağıranlar — regresyon senaryoları", () => {
    it("AC-9: Mevcut çağıran — <Button className='bg-red-600'>Kaldır</Button> — className'de bg-red-600 BULUNMALI", () => {
      const { container } = render(
        <Button className="bg-red-600">Kaldır</Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-red-600");
    });

    it("AC-9: Mevcut çağıran — <Button className='bg-red-600'>Kaldır</Button> — className'de bg-success BULUNMAMALI (override)", () => {
      const { container } = render(
        <Button className="bg-red-600">Kaldır</Button>
      );
      const btn = container.querySelector("button");
      // Token check: "hover:bg-success/90" legitimately stays; only the base bg is overridden.
      expect(btn?.className.split(" ")).not.toContain("bg-success");
    });

    it("AC-9: Mevcut çağıran — <Button className='bg-green-50 hover:bg-green-100'> — className'de bg-green-50 BULUNMALI", () => {
      const { container } = render(
        <Button className="bg-green-50 hover:bg-green-100">Onayla</Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-green-50");
    });

    it("AC-9: Mevcut çağıran — <Button className='bg-green-50 hover:bg-green-100'> — className'de hover:bg-green-100 BULUNMALI", () => {
      const { container } = render(
        <Button className="bg-green-50 hover:bg-green-100">Onayla</Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("hover:bg-green-100");
    });

    it("AC-9: Mevcut çağıran — <Button className='px-2 py-1 text-xs'>Ufak</Button> — className'de px-2 BULUNMALI", () => {
      const { container } = render(
        <Button className="px-2 py-1 text-xs">Ufak</Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("px-2");
    });

    it("AC-9: Mevcut çağıran — <Button className='px-2 py-1 text-xs'>Ufak</Button> — className'de py-1 BULUNMALI", () => {
      const { container } = render(
        <Button className="px-2 py-1 text-xs">Ufak</Button>
      );
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("py-1");
    });
  });
});
