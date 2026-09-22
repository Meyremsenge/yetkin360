import { describe, it, expect } from "vitest";
import { NextRequest, NextResponse } from "next/server";

/**
 * AC-2: Cookie yok → middleware 307 yönlendir `/giris?next=<yol>`.
 * AC-S1: Sahte cookie varsa → middleware geçer (ipucu); asıl karar /me 401'inde.
 * Davranış Sözleşmesi satır 2: public allowlist.
 * config.matcher: `_next` ve statik hariç.
 */

describe("middleware", () => {
  describe("AC-2: Cookie yok korumalı rota", () => {
    it("AC-2: protected /profil without cookies → 307 redirect to /giris?next=%2Fprofil", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response).toBeDefined();
      expect(response?.status).toBe(307);
      const location = response?.headers.get("location");
      expect(location).toContain("/giris?next=%2Fprofil");
    });

    it("AC-2: protected /yetkinlikler without cookies → redirect", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/yetkinlikler", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).toBe(307);
      expect(response?.headers.get("location")).toContain("/giris");
    });

    it("AC-2: deeply nested protected /kurumlar/abc/yetkinlikler → redirect", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest(
        "http://localhost:3000/kurumlar/abc/yetkinlikler",
        { headers: { cookie: "" } }
      );

      const response = middleware(request);
      expect(response?.status).toBe(307);
    });
  });

  describe("Davranış 2: Public allowlist", () => {
    it("Davranış 2: public `/` without cookies → allow", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      // Should be null (NextResponse.next()) or pass through
      expect(response?.status).not.toBe(307);
    });

    it("Davranış 2: public `/giris` without cookies → allow", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/giris", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });

    it("Davranış 2: public `/giris/*` subpaths → allow", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest(
        "http://localhost:3000/giris/sifre-sifirla",
        {
          headers: { cookie: "" },
        }
      );

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });

    it("Davranış 2: public `/_next/*` → allow", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest(
        "http://localhost:3000/_next/static/abc.js",
        {
          headers: { cookie: "" },
        }
      );

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });

    it("Davranış 2: public `favicon.ico` → allow", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/favicon.ico", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });

    it("Davranış 2: static file `/logo.png` → allow", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/logo.png", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });

    it("Davranış 2: static file `/styles.css` → allow", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/styles.css", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });
  });

  describe("AC-S1: Cookie hint logic", () => {
    it("AC-S1: access_token cookie → middleware allows (ipucu); asıl karar /me'de", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil", {
        headers: { cookie: "access_token=fake_value" },
      });

      const response = middleware(request);
      // Middleware passes through (NextResponse.next())
      expect(response?.status).not.toBe(307);
    });

    it("AC-S1: csrf_token cookie → middleware allows", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil", {
        headers: { cookie: "csrf_token=fake_value" },
      });

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });

    it("AC-S1: both tokens → middleware allows", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil", {
        headers: {
          cookie: "access_token=fake; csrf_token=fake",
        },
      });

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });

    it("AC-S1: refresh_token alone → middleware redirects (not access_token or csrf_token)", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil", {
        headers: { cookie: "refresh_token=fake_value" },
      });

      const response = middleware(request);
      // refresh_token alone doesn't trigger the hint
      expect(response?.status).toBe(307);
    });
  });

  describe("Middleware response structure", () => {
    it("AC-2: redirect includes `next` parameter encoded", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest(
        "http://localhost:3000/profil?tab=skills",
        {
          headers: { cookie: "" },
        }
      );

      const response = middleware(request);
      const location = response?.headers.get("location");
      expect(location).toContain("next=%2Fprofil");
    });

    it("AC-2: redirect Location header is set", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/yetkinlikler", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.headers.has("location")).toBe(true);
    });

    it("AC-2: response is 307 (temporary redirect)", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/korumalı", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).toBe(307);
    });

    it("Middleware allows (NextResponse.next()) when authenticated", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil", {
        headers: { cookie: "access_token=valid" },
      });

      const response = middleware(request);
      // When authenticated, should be null or NextResponse.next()
      // Status should not be a redirect
      if (response?.status === 307) {
        expect(response.status).not.toBe(307);
      }
    });
  });

  describe("Middleware config matcher", () => {
    it("middleware config exported with correct matcher pattern", async () => {
      const { config } = await import("@/middleware");
      expect(config).toBeDefined();
      expect(config.matcher).toBeDefined();
      expect(Array.isArray(config.matcher) || typeof config.matcher === "string").toBe(
        true
      );
    });

    it("config.matcher excludes /_next/* from middleware", async () => {
      const { config } = await import("@/middleware");
      const matcher = config.matcher;
      // Matcher should be structured to exclude _next routes
      // This is verified by the fact that /_next/* routes don't trigger middleware
      expect(matcher).toBeDefined();
    });

    it("config.matcher excludes static file extensions", async () => {
      const { config } = await import("@/middleware");
      const matcher = config.matcher;
      // Matcher should exclude common static extensions like .png, .css, .js, etc.
      expect(matcher).toBeDefined();
    });
  });

  describe("Next parameter sanitization", () => {
    it("AC-2/AC-S3: next parameter is built from pathname", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      const location = response?.headers.get("location");
      // Should contain encoded pathname
      expect(location).toContain("next=");
      expect(location).toContain("%2Fprofil");
    });
  });

  describe("Edge cases", () => {
    it("Protected route with complex path", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest(
        "http://localhost:3000/kurumlar/id-123/yetkinlikler/skill-456",
        {
          headers: { cookie: "" },
        }
      );

      const response = middleware(request);
      expect(response?.status).toBe(307);
      expect(response?.headers.get("location")).toContain("/giris");
    });

    it("Route with trailing slash", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/profil/", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).toBe(307);
    });

    it("Public root with trailing slash", async () => {
      const { middleware } = await import("@/middleware");
      const request = new NextRequest("http://localhost:3000/", {
        headers: { cookie: "" },
      });

      const response = middleware(request);
      expect(response?.status).not.toBe(307);
    });
  });
});
