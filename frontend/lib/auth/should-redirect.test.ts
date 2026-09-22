import { describe, it, expect } from "vitest";
import { buildLoginUrl, shouldRedirect } from "@/lib/auth/should-redirect";

/**
 * AC-2: Cookie yok → middleware 307 ile yönlendir.
 * AC-S1: Sahte cookie var → shouldRedirect null döner (ipucu), middleware geçer; asıl karar /me 401'inde.
 * AC-S3: next parametresi doğrulanır.
 * Davranış Sözleşmesi satır 2: public allowlist.
 */

describe("buildLoginUrl", () => {
  it("builds /giris?next=<encoded-pathname>", () => {
    const url = buildLoginUrl("/profil");
    expect(url).toBe("/giris?next=%2Fprofil");
  });

  it("encodes special characters in pathname", () => {
    const url = buildLoginUrl("/yetkinlikler/abc?foo=bar");
    expect(url).toContain("next=");
    expect(url).toContain("%2F");
    expect(url).toContain("%3F");
    expect(url).toContain("%3D");
  });

  it("adds &neden=oturum-bitti when reason='oturum-bitti'", () => {
    const url = buildLoginUrl("/profil", "oturum-bitti");
    expect(url).toBe("/giris?next=%2Fprofil&neden=oturum-bitti");
  });

  it("ignores reason if not provided", () => {
    const url = buildLoginUrl("/profil", undefined);
    expect(url).toBe("/giris?next=%2Fprofil");
  });
});

describe("shouldRedirect", () => {
  describe("Public allowlist routes", () => {
    it("AC-2 / Davranış 2: allows `/` without cookies", () => {
      expect(shouldRedirect("/", [])).toBeNull();
    });

    it("Davranış 2: allows `/giris` without cookies", () => {
      expect(shouldRedirect("/giris", [])).toBeNull();
    });

    it("Davranış 2: allows `/giris/*` subpaths without cookies", () => {
      expect(shouldRedirect("/giris/sifre-sifirla", [])).toBeNull();
      expect(shouldRedirect("/giris/email-dogrula", [])).toBeNull();
    });

    it("AC-1: allows `/kayit` without cookies (registration page)", () => {
      expect(shouldRedirect("/kayit", [])).toBeNull();
    });

    it("AC-1: allows `/kayit/*` subpaths without cookies", () => {
      expect(shouldRedirect("/kayit/confirm", [])).toBeNull();
    });

    it("AC-5/AC-6: allows `/e-posta-dogrula` without cookies (email verification page)", () => {
      expect(shouldRedirect("/e-posta-dogrula", [])).toBeNull();
    });

    it("AC-5/AC-6: allows `/e-posta-dogrula/*` subpaths without cookies", () => {
      expect(shouldRedirect("/e-posta-dogrula?token=abc", [])).toBeNull();
    });

    it("AC-7/AC-S2: allows `/sifre-unuttum` without cookies (forgot password page)", () => {
      expect(shouldRedirect("/sifre-unuttum", [])).toBeNull();
    });

    it("AC-7/AC-S2: allows `/sifre-unuttum/*` subpaths without cookies", () => {
      expect(shouldRedirect("/sifre-unuttum/confirm", [])).toBeNull();
    });

    it("AC-8/AC-6: allows `/sifre-sifirla` without cookies (password reset page)", () => {
      expect(shouldRedirect("/sifre-sifirla", [])).toBeNull();
    });

    it("AC-8/AC-6: allows `/sifre-sifirla/*` subpaths without cookies", () => {
      expect(shouldRedirect("/sifre-sifirla?token=xyz", [])).toBeNull();
    });

    it("Davranış 2: allows `/_next/*` (Next.js internals)", () => {
      expect(shouldRedirect("/_next/image", [])).toBeNull();
      expect(shouldRedirect("/_next/static/abc", [])).toBeNull();
    });

    it("Davranış 2: allows `favicon.ico`", () => {
      expect(shouldRedirect("/favicon.ico", [])).toBeNull();
    });

    it("Davranış 2: allows static files with extensions", () => {
      expect(shouldRedirect("/logo.png", [])).toBeNull();
      expect(shouldRedirect("/styles.css", [])).toBeNull();
      expect(shouldRedirect("/app.js", [])).toBeNull();
      expect(shouldRedirect("/data.json", [])).toBeNull();
      expect(shouldRedirect("/font.woff2", [])).toBeNull();
    });

    it("Davranış 2: rejects files without extension in protected routes", () => {
      const redirect = shouldRedirect("/profil", []);
      expect(redirect).not.toBeNull();
      expect(redirect).toContain("/giris");
    });
  });

  describe("Cookie-based gating", () => {
    it("AC-2: redirects when no access_token or csrf_token", () => {
      const redirect = shouldRedirect("/profil", []);
      expect(redirect).not.toBeNull();
      expect(redirect).toContain("/giris?next=%2Fprofil");
    });

    it("AC-2: redirects when empty cookie array", () => {
      const redirect = shouldRedirect("/yetkinlikler", []);
      expect(redirect).not.toBeNull();
    });

    it("AC-S1: allows access when access_token present (even if fake)", () => {
      // Middleware hint only; real decision at /me 401
      expect(shouldRedirect("/profil", ["access_token"])).toBeNull();
    });

    it("AC-S1: allows access when csrf_token present (even if fake)", () => {
      // Middleware hint only; real decision at /me 401
      expect(shouldRedirect("/profil", ["csrf_token"])).toBeNull();
    });

    it("AC-S1: allows access when both tokens present", () => {
      expect(
        shouldRedirect("/profil", ["access_token", "csrf_token"])
      ).toBeNull();
    });

    it("AC-S1: requires access_token OR csrf_token; refresh_token alone insufficient", () => {
      // refresh_token is path-restricted to /auth/refresh, so middleware can't see it
      // This test verifies refresh_token alone does NOT grant access
      const redirect = shouldRedirect("/profil", ["refresh_token"]);
      expect(redirect).not.toBeNull();
      expect(redirect).toContain("/giris");
    });

    it("AC-S1: allows with access_token even if other cookies present", () => {
      expect(
        shouldRedirect("/profil", ["session_id", "access_token", "other"])
      ).toBeNull();
    });

    it("AC-S1: allows with csrf_token even if other cookies present", () => {
      expect(
        shouldRedirect("/profil", ["session_id", "csrf_token", "other"])
      ).toBeNull();
    });
  });

  describe("Protected routes", () => {
    it("AC-2: redirects protected /profil when unauthenticated", () => {
      const redirect = shouldRedirect("/profil", []);
      expect(redirect).toBe("/giris?next=%2Fprofil");
    });

    it("AC-2: redirects protected /yetkinlikler when unauthenticated", () => {
      const redirect = shouldRedirect("/yetkinlikler", []);
      expect(redirect).toBe("/giris?next=%2Fyetkinlikler");
    });

    it("AC-2: redirects arbitrarily nested protected routes", () => {
      const redirect = shouldRedirect("/kurumlar/abc-123/yetkinlikler", []);
      expect(redirect).toBe("/giris?next=%2Fkurumlar%2Fabc-123%2Fyetkinlikler");
    });
  });

  describe("AC-S3: next parameter sanitization", () => {
    it("redirects to /giris with encoded valid pathname", () => {
      const redirect = shouldRedirect("/profil", []);
      expect(redirect).toBe("/giris?next=%2Fprofil");
    });

    // Sanitization logic is tested in sanitize-next.test.ts
    // Here we verify shouldRedirect uses it correctly by checking result structure
    it("result is a valid login URL with ?next=", () => {
      const redirect = shouldRedirect("/some/path", []);
      expect(redirect).toMatch(/^\/giris\?next=/);
    });
  });

  describe("Edge cases", () => {
    it("handles root path /", () => {
      expect(shouldRedirect("/", [])).toBeNull();
    });

    it("handles path with query parameters", () => {
      const redirect = shouldRedirect("/profil?tab=skills", []);
      expect(redirect).toContain("/giris");
      expect(redirect).toContain("next=");
    });

    it("handles path with fragments", () => {
      const redirect = shouldRedirect("/profil#section", []);
      expect(redirect).toContain("/giris");
    });

    it("handles uppercase cookie names (case-sensitive check)", () => {
      // Cookie names are case-sensitive in the array passed
      expect(shouldRedirect("/profil", ["ACCESS_TOKEN"])).not.toBeNull();
      expect(shouldRedirect("/profil", ["access_token"])).toBeNull();
    });
  });
});
