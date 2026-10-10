/**
 * Recipients of an approval request: e-mail addresses typed into one box,
 * separated by commas, semicolons or whitespace. At least one is required.
 *
 * Format check only (same rule as the backend); whether an address belongs to
 * a coordinator of the institution is decided by the server.
 */

export const MAX_NOTIFY_EMAILS = 5;

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export type NotifyEmailsResult =
  | { ok: true; emails: string[] }
  | { ok: false; error: "invalid"; email: string }
  | { ok: false; error: "required" }
  | { ok: false; error: "tooMany" };

export function parseNotifyEmails(input: string): NotifyEmailsResult {
  const seen = new Set<string>();
  const emails: string[] = [];

  for (const part of input.split(/[\s,;]+/)) {
    if (!part) continue;
    if (!EMAIL_PATTERN.test(part)) return { ok: false, error: "invalid", email: part };
    const key = part.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    emails.push(part);
  }

  if (emails.length === 0) return { ok: false, error: "required" };
  if (emails.length > MAX_NOTIFY_EMAILS) return { ok: false, error: "tooMany" };
  return { ok: true, emails };
}
