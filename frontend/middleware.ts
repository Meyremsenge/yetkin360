/**
 * AC-2/AC-S1: Middleware routing gate.
 * Edge runtime — no Node APIs.
 * Cookie hint logic extracted to shouldRedirect (pure function).
 * JWT validation ONLY a routing hint — real security decision at /me 401.
 */

import { NextRequest, NextResponse } from "next/server";
import { shouldRedirect } from "@/lib/auth/should-redirect";

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Extract cookie names from Cookie header
  const cookieHeader = request.headers.get("cookie") || "";
  const cookieNames = parseCookieNames(cookieHeader);

  // Decide redirect (saf fonksiyon)
  const redirect = shouldRedirect(pathname, cookieNames);

  if (redirect) {
    return NextResponse.redirect(new URL(redirect, request.url), { status: 307 });
  }

  return NextResponse.next();
}

function parseCookieNames(cookieHeader: string): string[] {
  return cookieHeader
    .split(";")
    .map((pair) => pair.trim().split("=")[0])
    .filter(Boolean);
}

export const config = {
  matcher: [
    // All paths except Next.js internals and static files with extensions
    "/((?!_next|.*\\.(?:ico|css|js|gif|jpeg|jpg|png|webp|svg|woff|woff2|ttf|eot|otf)).*)",
  ],
};
