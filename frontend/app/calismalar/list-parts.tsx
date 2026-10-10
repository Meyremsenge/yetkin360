import { cn } from "@/lib/utils";
import { CHAIN_PROGRESS, type StatusTone } from "@/lib/ui/engagement-chain";
import messages from "@/messages/tr.json";

/** Pieces shared by the student list and the organization/institution list. */

export const DOT_CLASS: Record<StatusTone, string> = {
  default: "bg-foreground",
  success: "bg-success",
  error: "bg-destructive",
  warning: "bg-warning",
};

// Hint chip colour follows the status badge.
export const CHIP_TONE: Record<StatusTone, string> = {
  default: "bg-muted text-foreground",
  warning: "bg-warning/10 text-warning",
  success: "bg-success/10 text-success",
  error: "bg-destructive/10 text-destructive",
};

export type TileTone = "ink" | "ochre" | "pine";

export const TONE_TILE: Record<TileTone, string> = {
  ink: "bg-muted text-foreground",
  ochre: "bg-warning/10 text-warning",
  pine: "bg-success/10 text-success",
};

export function formatTemplate(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replace(`{${key}}`, String(value)),
    template,
  );
}

export function relativeTime(iso: string, now: number = Date.now()): string {
  const rel = messages.calismalar.relative;
  const seconds = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return rel.now;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return formatTemplate(rel.minutes, { n: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return formatTemplate(rel.hours, { n: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return formatTemplate(rel.days, { n: days });
  if (days < 30) return formatTemplate(rel.weeks, { n: Math.floor(days / 7) });
  if (days < 365) return formatTemplate(rel.months, { n: Math.floor(days / 30) });
  return formatTemplate(rel.years, { n: Math.floor(days / 365) });
}

export function fullDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Relative time with the full date on hover. */
export function TimeAgo({ iso }: { iso: string }) {
  return (
    <time dateTime={iso} title={fullDate(iso)} className="font-mono text-xs text-muted-foreground">
      {relativeTime(iso)}
    </time>
  );
}

export function MiniChain({ status }: { status: string }) {
  const { done, broken } = CHAIN_PROGRESS[status] ?? { done: 0 };
  const label = broken
    ? formatTemplate(messages.calismalar.chainBrokenLabel, { step: broken })
    : formatTemplate(messages.calismalar.chainLabel, { done });

  return (
    <span role="img" aria-label={label} className="flex items-center">
      {[1, 2, 3, 4].map((step) => {
        const isDone = step <= done;
        const isBroken = step === broken;
        return (
          <span key={step} className="flex items-center" aria-hidden="true">
            {step > 1 ? (
              <span className={cn("h-px w-3", step <= done ? "bg-success" : "bg-border")} />
            ) : null}
            <span
              className={cn(
                "h-2 w-2 rounded-full border",
                isDone && "border-success bg-success",
                isBroken && "border-destructive bg-destructive/10",
                !isDone && !isBroken && "border-border bg-card",
              )}
            />
          </span>
        );
      })}
    </span>
  );
}

export function SealMark() {
  return (
    <span
      data-testid="calismalar-verified-mark"
      className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success text-background"
    >
      <svg
        viewBox="0 0 24 24"
        className="h-3 w-3"
        fill="none"
        stroke="currentColor"
        strokeWidth={3}
        aria-hidden="true"
      >
        <path d="M5 12l5 5L20 7" />
      </svg>
    </span>
  );
}

export function ArrowIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={cn("h-3.5 w-3.5", className)} fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Line icon in a toned tile, used by the count tiles. */
export function TileIcon({ path, tone }: { path: string; tone: TileTone }) {
  return (
    <span className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-lg", TONE_TILE[tone])}>
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d={path} />
      </svg>
    </span>
  );
}

// One quiet line icon per engagement kind (lucide shapes, inline).
export function KindIcon({ kind }: { kind: string }) {
  const paths: Record<string, string> = {
    INTERNSHIP: "M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16M4 6h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z",
    CAPSTONE: "M22 10 12 5 2 10l10 5 10-5zM6 12v5c3 2 9 2 12 0v-5",
    SHORT_PROJECT: "M13 2 3 14h9l-1 8 10-12h-9l1-8z",
    PART_TIME: "M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  };
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-[18px] w-[18px]"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[kind] ?? paths.INTERNSHIP} />
    </svg>
  );
}

export const TILE_ICON = {
  briefcase:
    "M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16M4 6h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z",
  clock: "M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  check: "M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4 12 14l-3-3",
  inbox: "M22 12h-6l-2 3h-4l-2-3H2M5.5 5h13l3.5 7v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z",
} as const;
