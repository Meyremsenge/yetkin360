import messages from "@/messages/tr.json";

const t = messages.publicProfile;

export function formatMonthYear(value: string): string {
  return new Date(value).toLocaleDateString("tr-TR", { month: "long", year: "numeric", timeZone: "UTC" });
}

export function formatPeriod(start: string | null, end: string | null): string | null {
  if (!start && !end) return null;
  return `${start ? formatMonthYear(start) : "–"} – ${end ? formatMonthYear(end) : messages.profil.ongoingLabel}`;
}

/** "6 hafta" under two months, otherwise rounded months ("3 ay"). */
export function formatDuration(start: string | null, end: string | null): string | null {
  if (!start || !end) return null;
  const days = Math.round((Date.parse(end) - Date.parse(start)) / 86_400_000);
  if (!Number.isFinite(days) || days <= 0) return null;
  if (days < 56) return t.durationWeeks.replace("{n}", String(Math.max(1, Math.round(days / 7))));
  return t.durationMonths.replace("{n}", String(Math.round(days / 30.44)));
}

export function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toLocaleUpperCase("tr-TR"))
    .join("");
}
