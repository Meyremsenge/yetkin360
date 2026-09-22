/**
 * AC-S3: Open redirect prevention.
 * Given `/giris?next=<değer>`, yalnız single-slash-prefixed relative paths accepted.
 * Everything else → `/`.
 */

export function sanitizeNext(value: string | null | undefined): string {
  if (!value) return "/";
  if (typeof value !== "string") return "/";
  if (value === "") return "/";

  // Must start with exactly one slash, no protocols or backslashes
  if (!value.startsWith("/")) return "/";

  // Reject double slash (//evil.com)
  if (value.startsWith("//")) return "/";

  // Reject protocols (http:, https:, javascript:, etc.)
  if (value.includes(":")) return "/";

  // Reject backslash (path traversal, Windows UNC)
  if (value.includes("\\")) return "/";

  // Reject control characters
  if (/[\x00-\x1f\x7f]/.test(value)) return "/";

  return value;
}
