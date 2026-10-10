"use client";

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

  const buttonClass =
    "px-3 py-1.5 text-sm border border-slate-300 rounded-md hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed";

  return (
    <nav
      aria-label={messages.adminPagination.nav}
      className="mt-4 flex items-center justify-between gap-4"
    >
      <button
        type="button"
        onClick={() => onChange(Math.max(0, offset - limit))}
        disabled={disabled || !hasPrevious}
        className={buttonClass}
      >
        {messages.adminPagination.previous}
      </button>
      <span aria-live="polite" className="text-sm text-slate-600">
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
