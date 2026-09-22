import { sanitizeNext } from "./sanitize-next";

/**
 * AC-2/AC-S1: Given pathname and cookie names, decide whether to redirect to login.
 * AC-S3: next parameter is sanitized.
 * Davranış Sözleşmesi satır 2: public allowlist.
 */

export function buildLoginUrl(
  pathname: string,
  reason?: "oturum-bitti"
): string {
  const sanitized = sanitizeNext(pathname);
  const encoded = encodeURIComponent(sanitized);
  const url = `/giris?next=${encoded}`;

  if (reason === "oturum-bitti") {
    return `${url}&neden=oturum-bitti`;
  }

  return url;
}

export function shouldRedirect(
  pathname: string,
  cookieNames: readonly string[]
): string | null {
  // Public allowlist (fail-closed: default redirect)
  if (isPublicRoute(pathname)) {
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
