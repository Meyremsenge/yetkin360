/**
 * SPRINT F: "Aday doğrula" — read a Yetkin360 link pasted from a CV.
 *
 * Only the path is used: whatever host the link names, the panel opens the
 * record on our own origin. That way a look-alike domain in a CV can not send
 * the reviewer elsewhere, and `javascript:`/`data:` input is never navigated to.
 */

export type CandidateLink = { kind: "verification"; token: string } | { kind: "profile"; slug: string };

const SEGMENT = /^[A-Za-z0-9_-]{1,200}$/;
const ALLOWED_SCHEMES = new Set(["http:", "https:"]);

function pathOf(input: string): string | null {
  if (input.startsWith("/")) return input;
  // Bare "host/v/..." without a scheme: read it as https.
  const candidate = /^[a-z][a-z0-9+.-]*:/i.test(input) ? input : `https://${input}`;
  let url: URL;
  try {
    url = new URL(candidate);
  } catch {
    return null;
  }
  if (!ALLOWED_SCHEMES.has(url.protocol)) return null;
  return url.pathname;
}

export function parseCandidateLink(raw: string): CandidateLink | null {
  const input = raw.trim();
  if (!input) return null;

  const path = pathOf(input);
  if (!path) return null;

  const match = /^\/(v|p)\/([^/?#]+)\/?$/.exec(path.split(/[?#]/)[0]);
  if (!match) return null;

  let segment: string;
  try {
    segment = decodeURIComponent(match[2]);
  } catch {
    return null;
  }
  if (!SEGMENT.test(segment)) return null;

  return match[1] === "v" ? { kind: "verification", token: segment } : { kind: "profile", slug: segment };
}

/** Same-origin path to open for a parsed link. */
export function candidateHref(link: CandidateLink): string {
  return link.kind === "verification"
    ? `/v/${encodeURIComponent(link.token)}`
    : `/p/${encodeURIComponent(link.slug)}`;
}
