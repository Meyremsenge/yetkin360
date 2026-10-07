import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./badge";

/**
 * ATDD — Badge bileşeni testleri
 * AC-7: Badge variant'ları — success/error/warning/default
 */

describe("Badge Component", () => {
  describe("AC-7: variant='success' — Aktif/İyi durumu", () => {
    it("AC-7: <Badge variant='success'>Aktif</Badge> children bulunmalı", () => {
      render(<Badge variant="success">Aktif</Badge>);
      expect(screen.getByText("Aktif")).toBeTruthy();
    });

    it("AC-7: <Badge variant='success'> className'de bg-success/10 BULUNMALI", () => {
      const { container } = render(
        <Badge variant="success">Aktif</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("bg-success/10");
    });

    it("AC-7: <Badge variant='success'> className'de text-success BULUNMALI", () => {
      const { container } = render(
        <Badge variant="success">Aktif</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("text-success");
    });
  });

  describe("AC-7: variant='error' — Hata/Kötü durumu", () => {
    it("AC-7: <Badge variant='error'> children bulunmalı", () => {
      render(<Badge variant="error">Hata</Badge>);
      expect(screen.getByText("Hata")).toBeTruthy();
    });

    it("AC-7: <Badge variant='error'> className'de bg-destructive/10 BULUNMALI", () => {
      const { container } = render(
        <Badge variant="error">Hata</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("bg-destructive/10");
    });

    it("AC-7: <Badge variant='error'> className'de text-destructive BULUNMALI", () => {
      const { container } = render(
        <Badge variant="error">Hata</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("text-destructive");
    });
  });

  describe("AC-7: variant='warning' — Uyarı durumu", () => {
    it("AC-7: <Badge variant='warning'> children bulunmalı", () => {
      render(<Badge variant="warning">Uyarı</Badge>);
      expect(screen.getByText("Uyarı")).toBeTruthy();
    });

    it("AC-7: <Badge variant='warning'> className'de bg-warning/10 BULUNMALI", () => {
      const { container } = render(
        <Badge variant="warning">Uyarı</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("bg-warning/10");
    });

    it("AC-7: <Badge variant='warning'> className'de text-warning BULUNMALI", () => {
      const { container } = render(
        <Badge variant="warning">Uyarı</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("text-warning");
    });
  });

  describe("AC-7: variant='default' (veya verilmez) — Varsayılan durum", () => {
    it("AC-7: <Badge variant='default'> children bulunmalı", () => {
      render(<Badge variant="default">Varsayılan</Badge>);
      expect(screen.getByText("Varsayılan")).toBeTruthy();
    });

    it("AC-7: <Badge variant='default'> className'de bg-muted BULUNMALI", () => {
      const { container } = render(
        <Badge variant="default">Varsayılan</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("bg-muted");
    });

    it("AC-7: <Badge variant='default'> className'de text-foreground BULUNMALI", () => {
      const { container } = render(
        <Badge variant="default">Varsayılan</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("text-foreground");
    });

    it("AC-7: <Badge> (variant verilmez) children bulunmalı", () => {
      render(<Badge>Varsayılan</Badge>);
      expect(screen.getByText("Varsayılan")).toBeTruthy();
    });

    it("AC-7: <Badge> (variant verilmez) className'de bg-muted BULUNMALI", () => {
      const { container } = render(<Badge>Varsayılan</Badge>);
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("bg-muted");
    });

    it("AC-7: <Badge> (variant verilmez) className'de text-foreground BULUNMALI", () => {
      const { container } = render(<Badge>Varsayılan</Badge>);
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("text-foreground");
    });
  });

  describe("AC-7: Badge temel stil'i (tüm variant'lar için)", () => {
    it("AC-7: <Badge variant='success'> className'de rounded BULUNMALI (yuvarlak köşeler)", () => {
      const { container } = render(
        <Badge variant="success">Test</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("rounded");
    });

    it("AC-7: <Badge variant='success'> className'de inline-flex BULUNMALI (satır içi)", () => {
      const { container } = render(
        <Badge variant="success">Test</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("inline-flex");
    });

    it("AC-7: <Badge variant='success'> className'de px BULUNMALI (yatay padding)", () => {
      const { container } = render(
        <Badge variant="success">Test</Badge>
      );
      const badge = container.querySelector("span");
      // px-2 veya px-3 olabilir, ama px (padding-x) olmalı
      expect(badge?.className).toMatch(/px-/);
    });

    it("AC-7: <Badge variant='success'> className'de py BULUNMALI (dikey padding)", () => {
      const { container } = render(
        <Badge variant="success">Test</Badge>
      );
      const badge = container.querySelector("span");
      // py-0.5 veya py-1 olabilir, ama py (padding-y) olmalı
      expect(badge?.className).toMatch(/py-/);
    });

    it("AC-7: <Badge variant='success'> className'de text-xs BULUNMALI (küçük yazı)", () => {
      const { container } = render(
        <Badge variant="success">Test</Badge>
      );
      const badge = container.querySelector("span");
      expect(badge?.className).toContain("text-xs");
    });
  });
});
