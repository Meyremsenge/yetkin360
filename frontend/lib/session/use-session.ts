"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useRouter, usePathname } from "next/navigation";
import { fetchMe } from "./fetch-me";
import { apiFetch } from "@/lib/api/client";
import { buildLoginUrl } from "@/lib/auth/should-redirect";
import {
  SessionExpiredError,
  InvalidResponseError,
  NetworkError,
  ApiError,
} from "@/lib/api/errors";

/**
 * AC-3: Query key for session state.
 * Used by TanStack Query to cache and invalidate session data.
 */
export const SESSION_QUERY_KEY = ["session"] as const;

/**
 * AC-3/AC-5: Determine whether to retry a failed session query.
 * - 4xx errors: no retry
 * - SessionExpiredError/InvalidResponseError: no retry
 * - NetworkError or ApiError >= 500: retry up to 2 times (failureCount < 2)
 * - Other errors: no retry
 */
export function sessionRetry(failureCount: number, error: unknown): boolean {
  // AC-3: ApiError with status < 500 → never retry
  if (error instanceof ApiError && error.status < 500) {
    return false;
  }

  // AC-4: SessionExpiredError → never retry
  if (error instanceof SessionExpiredError) {
    return false;
  }

  // AC-7: InvalidResponseError → never retry
  if (error instanceof InvalidResponseError) {
    return false;
  }

  // AC-5: NetworkError or ApiError >= 500 → retry max 2 times
  if (error instanceof NetworkError || (error instanceof ApiError && error.status >= 500)) {
    return failureCount < 2;
  }

  // Other errors → no retry
  return false;
}

/**
 * AC-1/AC-4: Hook to manage session state.
 * Returns useQuery result: { data, error, isPending, isError, ... }
 * On SessionExpiredError: clears cache and redirects to login.
 */
export function useSession() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const hasHandledExpired = useRef(false);
  const routerRef = useRef(router);
  const pathnameRef = useRef(pathname);

  // Update refs to always have latest values. Bir effect içinde yapılır
  // (render sırasında değil) — React 19 sonrası eslint-plugin-react-hooks
  // bunu "render sırasında ref mutasyonu" olarak yasaklıyor; efektlerin
  // bildirim sırasına göre çalışması aşağıdaki SessionExpiredError
  // efektinden ÖNCE tetiklenmesini garantiler, davranış değişmiyor.
  useEffect(() => {
    routerRef.current = router;
    pathnameRef.current = pathname;
  }, [router, pathname]);

  const query = useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: fetchMe,
    retry: sessionRetry,
  });

  // AC-4/AC-S1: Handle SessionExpiredError once
  useEffect(() => {
    if (
      query.isError &&
      query.error instanceof SessionExpiredError &&
      !hasHandledExpired.current
    ) {
      hasHandledExpired.current = true;

      // AC-S5: Clear all cache
      queryClient.clear();

      // AC-4: Redirect to login with reason
      const loginUrl = buildLoginUrl(pathnameRef.current, "oturum-bitti");
      if (routerRef.current?.replace) {
        routerRef.current.replace(loginUrl);
      }
    }
  }, [query.isError, query.error, queryClient]);

  return query;
}

/**
 * AC-8: Hook for logout.
 * Returns { logout, isPending, isError }.
 * logout() never rejects — errors are captured in isError.
 * Success: clears cache and redirects.
 * Error: sets isError but preserves cache and session state.
 */
export function useLogout(): {
  logout: () => Promise<void>;
  isPending: boolean;
  isError: boolean;
} {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [isError, setIsError] = useState(false);

  const mutation = useMutation({
    mutationFn: async () => {
      await apiFetch("/auth/logout", { method: "POST" });
    },
    onSuccess: () => {
      // AC-8: Success → clear cache and redirect
      setIsError(false);
      queryClient.clear();
      if (router?.replace) {
        router.replace("/giris");
      }
    },
    onError: () => {
      // AC-8: Error → preserve cache, set error flag
      setIsError(true);
    },
  });

  return {
    logout: async () => {
      // AC-8: Reset error flag on new attempt
      setIsError(false);

      try {
        await mutation.mutateAsync();
      } catch {
        // AC-8: Never reject — swallow error and let isError flag indicate failure
      }
    },
    isPending: mutation.isPending,
    isError,
  };
}
