import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Alert } from "./alert";

/**
 * ATDD — Alert bileşeni testleri
 * AC-6: Alert variant'ları — error/success/warning/info
 */

describe("Alert Component", () => {
  describe("AC-6: variant='error' — Hata durumu", () => {
    it("AC-6: <Alert variant='error'>Mesaj</Alert> children bulunmalı", () => {
      render(<Alert variant="error">Hata mesajı</Alert>);
      expect(screen.getByText("Hata mesajı")).toBeTruthy();
    });

    it("AC-6: <Alert variant='error'> className'de bg-destructive/10 BULUNMALI", () => {
      const { container } = render(
        <Alert variant="error">Hata</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("bg-destructive/10");
    });

    it("AC-6: <Alert variant='error'> className'de text-destructive BULUNMALI", () => {
      const { container } = render(
        <Alert variant="error">Hata</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("text-destructive");
    });

    it("AC-6: <Alert variant='error'> className'de border-destructive/30 BULUNMALI", () => {
      const { container } = render(
        <Alert variant="error">Hata</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border-destructive/30");
    });
  });

  describe("AC-6: variant='success' — Başarı durumu", () => {
    it("AC-6: <Alert variant='success'> children bulunmalı", () => {
      render(<Alert variant="success">Başarılı</Alert>);
      expect(screen.getByText("Başarılı")).toBeTruthy();
    });

    it("AC-6: <Alert variant='success'> className'de bg-success/10 BULUNMALI", () => {
      const { container } = render(
        <Alert variant="success">Başarılı</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("bg-success/10");
    });

    it("AC-6: <Alert variant='success'> className'de text-success BULUNMALI", () => {
      const { container } = render(
        <Alert variant="success">Başarılı</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("text-success");
    });

    it("AC-6: <Alert variant='success'> className'de border-success/30 BULUNMALI", () => {
      const { container } = render(
        <Alert variant="success">Başarılı</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border-success/30");
    });
  });

  describe("AC-6: variant='warning' — Uyarı durumu", () => {
    it("AC-6: <Alert variant='warning'> children bulunmalı", () => {
      render(<Alert variant="warning">Uyarı</Alert>);
      expect(screen.getByText("Uyarı")).toBeTruthy();
    });

    it("AC-6: <Alert variant='warning'> className'de bg-warning/10 BULUNMALI", () => {
      const { container } = render(
        <Alert variant="warning">Uyarı</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("bg-warning/10");
    });

    it("AC-6: <Alert variant='warning'> className'de text-warning BULUNMALI", () => {
      const { container } = render(
        <Alert variant="warning">Uyarı</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("text-warning");
    });

    it("AC-6: <Alert variant='warning'> className'de border-warning/30 BULUNMALI", () => {
      const { container } = render(
        <Alert variant="warning">Uyarı</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border-warning/30");
    });
  });

  describe("AC-6: variant='info' (veya verilmez) — Bilgi/Varsayılan durumu", () => {
    it("AC-6: <Alert variant='info'> children bulunmalı", () => {
      render(<Alert variant="info">Bilgi</Alert>);
      expect(screen.getByText("Bilgi")).toBeTruthy();
    });

    it("AC-6: <Alert variant='info'> className'de bg-muted BULUNMALI", () => {
      const { container } = render(
        <Alert variant="info">Bilgi</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("bg-muted");
    });

    it("AC-6: <Alert variant='info'> className'de text-foreground BULUNMALI", () => {
      const { container } = render(
        <Alert variant="info">Bilgi</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("text-foreground");
    });

    it("AC-6: <Alert variant='info'> className'de border-border BULUNMALI", () => {
      const { container } = render(
        <Alert variant="info">Bilgi</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border-border");
    });

    it("AC-6: <Alert> (variant verilmez) children bulunmalı", () => {
      render(<Alert>Varsayılan</Alert>);
      expect(screen.getByText("Varsayılan")).toBeTruthy();
    });

    it("AC-6: <Alert> (variant verilmez) className'de bg-muted BULUNMALI", () => {
      const { container } = render(<Alert>Varsayılan</Alert>);
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("bg-muted");
    });

    it("AC-6: <Alert> (variant verilmez) className'de text-foreground BULUNMALI", () => {
      const { container } = render(<Alert>Varsayılan</Alert>);
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("text-foreground");
    });

    it("AC-6: <Alert> (variant verilmez) className'de border-border BULUNMALI", () => {
      const { container } = render(<Alert>Varsayılan</Alert>);
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border-border");
    });
  });

  describe("AC-6: Alert temel stil'i (tüm variant'lar için)", () => {
    it("AC-6: <Alert variant='error'> className'de border BULUNMALI (kenarlık tanımlı)", () => {
      const { container } = render(
        <Alert variant="error">Test</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border");
    });

    it("AC-6: <Alert variant='error'> className'de rounded BULUNMALI (yuvarlak köşeler)", () => {
      const { container } = render(
        <Alert variant="error">Test</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("rounded");
    });

    it("AC-6: <Alert variant='error'> className'de p (padding) BULUNMALI", () => {
      const { container } = render(
        <Alert variant="error">Test</Alert>
      );
      const alert = container.querySelector("div");
      // p-3, p-4, p-6 gibi padding class'ı olmalı
      expect(alert?.className).toMatch(/p-\d/);
    });

    it("AC-6: <Alert variant='success'> className'de border BULUNMALI", () => {
      const { container } = render(
        <Alert variant="success">Test</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border");
    });

    it("AC-6: <Alert variant='warning'> className'de border BULUNMALI", () => {
      const { container } = render(
        <Alert variant="warning">Test</Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("border");
    });
  });

  describe("AC-6: Alert className override desteği", () => {
    it("AC-6: <Alert variant='error' className='mt-4'> className'de mt-4 BULUNMALI", () => {
      const { container } = render(
        <Alert variant="error" className="mt-4">
          Test
        </Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("mt-4");
    });

    it("AC-6: <Alert variant='error' className='mt-4'> hala bg-destructive/10 içerir", () => {
      const { container } = render(
        <Alert variant="error" className="mt-4">
          Test
        </Alert>
      );
      const alert = container.querySelector("div");
      expect(alert?.className).toContain("bg-destructive/10");
    });
  });
});
