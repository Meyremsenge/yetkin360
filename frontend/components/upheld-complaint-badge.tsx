import { isUpheldBadgeVisible } from "@/lib/complaints/rules";
import messages from "@/messages/tr.json";

/**
 * C7 damga: shows how many verification requests an institution/organization left
 * unanswered (upheld complaints). Renders NOTHING for 0 / null / undefined (AC-18).
 * Public: carries only the count — no complaint text or identities (AC-S13).
 */
export function UpheldComplaintBadge({ count }: { count: number | null | undefined }) {
  if (!isUpheldBadgeVisible(count)) return null;
  const text = messages.complaints.badge.text.replace("{count}", String(count));
  return (
    <span
      title={messages.complaints.badge.label}
      className="inline-flex items-center gap-1.5 rounded-full border border-destructive/40 bg-destructive/10 px-2.5 py-1 text-xs font-semibold text-destructive"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-3.5 w-3.5 shrink-0">
        <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      </svg>
      {text}
    </span>
  );
}
