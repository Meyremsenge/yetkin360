"use client";

import { actionClass } from "@/components/panel-kit";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

interface AdminPaginationProps {
  offset: number;
  limit: number;
  hasMore: boolean;
  disabled?: boolean;
  onChange: (nextOffset: number) => void;
}

/** Previous/Next controls for the admin list screens (server-side paging). */
export function AdminPagination({ offset, limit, hasMore, disabled, onChange }: AdminPaginationProps) {
  const page = Math.floor(offset / limit) + 1;
  const hasPrevious = offset > 0;
  if (!hasPrevious && !hasMore) return null;

  const buttonClass = cn(actionClass.neutral, "h-8 px-3 text-xs");

  return (
    <nav
      aria-label={messages.adminPagination.nav}
      className="flex items-center justify-between gap-4 border-t border-border px-5 py-3"
    >
      <button
        type="button"
        onClick={() => onChange(Math.max(0, offset - limit))}
        disabled={disabled || !hasPrevious}
        className={buttonClass}
      >
        {messages.adminPagination.previous}
      </button>
      <span aria-live="polite" className="text-sm text-muted-foreground">
        {messages.adminPagination.page} {page}
      </span>
      <button
        type="button"
        onClick={() => onChange(offset + limit)}
        disabled={disabled || !hasMore}
        className={buttonClass}
      >
        {messages.adminPagination.next}
      </button>
    </nav>
  );
}
