import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { QrCode } from "./qr-code";

describe("QrCode", () => {
  afterEach(() => cleanup());

  it("renders an accessible SVG with a quiet zone and dark modules", () => {
    render(<QrCode value="https://example.test/p/ayse-yilmaz" label="Profil QR" />);

    const svg = screen.getByRole("img", { name: "Profil QR" });
    const [, , w, h] = (svg.getAttribute("viewBox") ?? "").split(" ").map(Number);
    // Version ≥ 1 is 21 modules; +4 quiet zone.
    expect(w).toBeGreaterThanOrEqual(25);
    expect(w).toBe(h);
    expect(svg.querySelector("path")?.getAttribute("d")).toMatch(/^M\d+ \d+h1v1h-1z/);
  });

  it("is deterministic and changes with the value", () => {
    const { rerender } = render(<QrCode value="a" label="q" />);
    const first = screen.getByRole("img").querySelector("path")?.getAttribute("d");
    rerender(<QrCode value="a" label="q" />);
    expect(screen.getByRole("img").querySelector("path")?.getAttribute("d")).toBe(first);
    rerender(<QrCode value="b" label="q" />);
    expect(screen.getByRole("img").querySelector("path")?.getAttribute("d")).not.toBe(first);
  });
});
