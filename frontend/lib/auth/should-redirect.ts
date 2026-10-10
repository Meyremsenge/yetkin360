import { sanitizeNext } from "./sanitize-next";

/**
 * AC-2/AC-S1: Given pathname and cookie names, decide whether to redirect to login.
 * AC-S3: next parameter is sanitized.
 * Davranış Sözleşmesi satır 2: public allowlist.
 */

const ADMIN_LOGIN_PATH = "/admin/giris";

function isAdminPath(pathname: string): boolean {
  const basePath = pathname.split("?")[0].split("#")[0];
  return basePath === "/admin" || basePath.startsWith("/admin/");
}

export function buildLoginUrl(
  pathname: string,
  reason?: "oturum-bitti"
): string {
  const sanitized = sanitizeNext(pathname);
  const encoded = encodeURIComponent(sanitized);
  // Admin pages send the visitor to the admin sign-in, not the student one.
  const loginPath = isAdminPath(sanitized) ? ADMIN_LOGIN_PATH : "/giris";
  const url = `${loginPath}?next=${encoded}`;

  if (reason === "oturum-bitti") {
    return `${url}&neden=oturum-bitti`;
  }

  return url;
}

export function shouldRedirect(
  pathname: string,
  cookieNames: readonly string[]
): string | null {
  // Extract base path (remove query params and hash)
  const basePath = pathname.split("?")[0].split("#")[0];

  // Public allowlist (fail-closed: default redirect)
  if (isPublicRoute(basePath)) {
    return null; // No redirect needed
  }

  // Check for auth hints: access_token OR csrf_token must be present
  const hasAccessToken = cookieNames.includes("access_token");
  const hasCsrfToken = cookieNames.includes("csrf_token");

  if (hasAccessToken || hasCsrfToken) {
    return null; // Hint: allow middleware to pass; real decision at /me 401
  }

  // Protected route without auth hint → redirect
  return buildLoginUrl(pathname);
}

function isPublicRoute(pathname: string): boolean {
  // Root
  if (pathname === "/") return true;

  // Login page and subpaths
  if (pathname === "/giris" || pathname.startsWith("/giris/")) return true;

  // Admin sign-in page only — every other /admin path stays protected
  if (pathname === ADMIN_LOGIN_PATH) return true;

  // Registration page and subpaths
  if (pathname === "/kayit" || pathname.startsWith("/kayit/")) return true;

  // Email verification page and subpaths
  if (pathname === "/e-posta-dogrula" || pathname.startsWith("/e-posta-dogrula/")) return true;

  // Forgot password page and subpaths
  if (pathname === "/sifre-unuttum" || pathname.startsWith("/sifre-unuttum/")) return true;

  // Reset password page and subpaths
  if (pathname === "/sifre-sifirla" || pathname.startsWith("/sifre-sifirla/")) return true;

  // Public profile page and subpaths
  if (pathname === "/p" || pathname.startsWith("/p/")) return true;

  // Public verification page and subpaths
  if (pathname === "/v" || pathname.startsWith("/v/")) return true;

  // Next.js internals
  if (pathname.startsWith("/_next/")) return true;

  // Favicon
  if (pathname === "/favicon.ico") return true;

  // Static files (has extension)
  if (hasExtension(pathname)) return true;

  return false;
}

function hasExtension(pathname: string): boolean {
  // Extract the last segment after the last /
  const lastSegment = pathname.split("/").pop() || "";
  // Has a dot and something after it (basic extension check)
  return lastSegment.includes(".");
}
