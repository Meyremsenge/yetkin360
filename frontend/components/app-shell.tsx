"use client";

import { ReactNode } from "react";
import { useSession, useLogout } from "@/lib/session/use-session";
import { ErrorBanner } from "@/components/error-banner";
import { Button } from "@/components/ui/button";
import {
  NetworkError,
  ApiError,
  SessionExpiredError,
  InvalidResponseError,
} from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export function AppShell({ children }: { children: ReactNode }) {
  const session = useSession();
  const logoutResult = useLogout();
  const logout = logoutResult || { logout: () => {}, isPending: false, isError: false };
  const logoutState = logout as ReturnType<typeof useLogout>;

  // AC-1: Loading state
  if (session.isPending) {
    return (
      <div aria-busy="true" className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-slate-600">{messages.shell.loading}</p>
        </div>
      </div>
    );
  }

  // AC-S1: SessionExpiredError → no children rendered
  if (session.error instanceof SessionExpiredError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <ErrorBanner
          message={messages.session.expired}
          onRetry={() => session.refetch()}
        />
      </div>
    );
  }

  // AC-7: InvalidResponseError
  if (session.error instanceof InvalidResponseError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <ErrorBanner
          message={messages.session.loadFailed}
          onRetry={() => session.refetch()}
        />
      </div>
    );
  }

  // AC-5: NetworkError or 5xx with no data → error screen
  if (session.error && !session.data) {
    let errorMessage = messages.errors.generic;
    let requestId: string | undefined;

    if (session.error instanceof NetworkError) {
      errorMessage =
        session.error.kind === "timeout"
          ? messages.errors.timeout
          : messages.errors.network;
    } else if (session.error instanceof ApiError) {
      errorMessage = messages.errors.generic;
      requestId = session.error.requestId || undefined;
    }

    return (
      <div className="flex items-center justify-center min-h-screen">
        <ErrorBanner
          message={errorMessage}
          requestId={requestId}
          onRetry={() => session.refetch()}
        />
      </div>
    );
  }

  // AC-1/AC-5: Happy path — render children (with optional error banner if data but error)
  return (
    <div>
      {/* AC-5: If there's an error but we have cached data, show both */}
      {Boolean(session.error) && session.data && (
        <div className="mb-4 mx-4 mt-4">
          {(() => {
            let errorMessage = messages.errors.generic;
            let requestId: string | undefined;

            if (session.error instanceof NetworkError) {
              errorMessage =
                session.error.kind === "timeout"
                  ? messages.errors.timeout
                  : messages.errors.network;
            } else if (session.error instanceof ApiError) {
              errorMessage = messages.errors.generic;
              requestId = session.error.requestId || undefined;
            }

            return (
              <ErrorBanner
                message={errorMessage}
                requestId={requestId}
                onRetry={() => session.refetch()}
              />
            );
          })()}
        </div>
      )}

      {/* AC-12: Empty state for organizations */}
      {session.data && session.data.organizations.length === 0 && (
        <div className="mb-4 mx-4 mt-4 rounded-md bg-blue-50 border border-blue-200 p-4 text-sm text-blue-700">
          {messages.shell.noOrganizations}
        </div>
      )}

      {/* AC-8: Logout error */}
      {logoutState.isError && (
        <div className="mb-4 mx-4 mt-4">
          <ErrorBanner message={messages.session.logoutFailed} />
        </div>
      )}

      {/* AC-1: Children render */}
      <div>
        {children}
      </div>

      {/* AC-8: Logout button */}
      {session.data && (
        <div className="flex justify-end p-4 border-t">
          <Button
            onClick={() => logoutState.logout()}
            className="bg-slate-600 hover:bg-slate-700"
          >
            {messages.session.logout}
          </Button>
        </div>
      )}
    </div>
  );
}
