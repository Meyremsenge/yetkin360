"use client";

import { ReactNode, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import messages from "@/messages/tr.json";

const ADMIN_LOGIN_PATH = "/admin/giris";

/**
 * UX guard for /admin/*: renders children only when `/me` says
 * `is_platform_admin === true`. Not a security boundary — every /admin API
 * call is gated on the server. The admin sign-in page is exempt (otherwise a
 * signed-out visitor would loop on the redirect).
 */
export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const session = useSession();

  const isLoginPage = pathname === ADMIN_LOGIN_PATH || pathname?.startsWith(`${ADMIN_LOGIN_PATH}/`);
  const isAdmin = session.data?.user?.is_platform_admin === true;
  // Redirect only once /me has resolved: pending or SessionExpiredError
  // (handled by useSession itself) must not trigger a second navigation.
  const shouldRedirect = !isLoginPage && !session.isPending && !session.isError && !isAdmin;

  useEffect(() => {
    if (shouldRedirect) router.replace(ADMIN_LOGIN_PATH);
  }, [shouldRedirect, router]);

  if (isLoginPage) return <>{children}</>;
  if (!isAdmin) {
    return (
      <p role="status" className="p-6 text-slate-600">
        {messages.adminHome.checking}
      </p>
    );
  }
  return <>{children}</>;
}
