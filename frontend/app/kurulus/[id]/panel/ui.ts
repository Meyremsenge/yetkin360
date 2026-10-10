import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export const FIELD_CLASS =
  "block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground transition-colors hover:border-muted-foreground/40 focus-visible:border-success focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/25";
export const LABEL_CLASS = "mb-1.5 block text-xs font-medium text-foreground";

export const UNIT_MAX_LENGTH = 60;

export function errorMessage(error: unknown): string {
  if (error instanceof SessionExpiredError) return messages.session.expired;
  if (error instanceof ApiError || error instanceof NetworkError) return error.message;
  return messages.errors.generic;
}
