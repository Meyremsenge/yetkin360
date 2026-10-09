"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import messages from "@/messages/tr.json";
import { StatusPageFrame, outlineLinkClass } from "./status-page-frame";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // AC-11: Move focus to heading on mount
  useEffect(() => {
    if (headingRef.current) {
      headingRef.current.focus();
    }
  }, []);

  const requestId =
    error instanceof ApiError ? error.requestId : undefined;

  return (
    <StatusPageFrame>
      <span
        aria-hidden="true"
        className="flex h-16 w-16 items-center justify-center rounded-full border border-destructive/30 bg-destructive/10 text-destructive"
      >
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth={1.5}>
          <path d="M12 4l9 16H3L12 4zM12 10v4M12 17.5v.01" />
        </svg>
      </span>

      <h1
        ref={headingRef}
        tabIndex={-1}
        className="mt-6 font-serif text-3xl font-semibold text-foreground focus:outline-none"
      >
        {messages.errorPage.title}
      </h1>

      <div role="alert" className="mt-2">
        <p className="text-[15px] text-muted-foreground">{messages.errors.generic}</p>

        {requestId != null && (
          <div className="mt-4 rounded-md border border-border bg-muted px-3 py-2 font-mono text-[13px] text-muted-foreground">
            {messages.errors.supportCode}
            {requestId ? `: ${requestId}` : ""}
          </div>
        )}
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        <Button
          onClick={reset}
          className="h-10 bg-success text-background hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
        >
          {messages.errors.retry}
        </Button>
        <Link href="/" className={outlineLinkClass}>
          {messages.notFound.home}
        </Link>
      </div>
    </StatusPageFrame>
  );
}
