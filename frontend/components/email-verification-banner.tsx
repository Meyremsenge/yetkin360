"use client";

import { useState } from "react";
import { resendVerification } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import messages from "@/messages/tr.json";

type ResendState = "idle" | "pending" | "sent" | "failed";

/**
 * YET-196: shown to signed-in users whose e-mail is not verified. Write endpoints
 * answer 401 EMAIL_NOT_VERIFIED for them, so this explains why and lets them request
 * a fresh link. The server always answers 204 (rate-limited calls are silent no-ops),
 * so "sent" never claims a mail was delivered.
 */
export function EmailVerificationBanner() {
  const [state, setState] = useState<ResendState>("idle");

  async function onResend() {
    setState("pending");
    try {
      await resendVerification();
      setState("sent");
    } catch {
      setState("failed");
    }
  }

  const text = messages.emailVerificationBanner;

  return (
    <div
      role="status"
      className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800"
    >
      <div className="font-medium">{text.message}</div>
      <div className="flex items-center gap-4 mt-3">
        <Button
          onClick={onResend}
          disabled={state === "pending"}
          className="bg-amber-600 hover:bg-amber-700 text-white px-3 py-1 text-sm"
        >
          {state === "pending" ? text.sending : text.resend}
        </Button>
        {state === "sent" && <span>{text.sent}</span>}
        {state === "failed" && (
          <span role="alert" className="text-red-700">
            {text.failed}
          </span>
        )}
      </div>
    </div>
  );
}
