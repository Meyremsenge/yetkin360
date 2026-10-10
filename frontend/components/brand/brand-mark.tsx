import { cn } from "@/lib/utils";
import {
  SEAL_CHECK_PATH,
  SEAL_CHECK_STROKE,
  SEAL_INNER_RING,
  SEAL_RING_PATH,
} from "./seal-geometry";

/** The Yetkin360 seal mark. Decorative unless `label` is given. */
export function SealMark({ className, label }: { className?: string; label?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={cn("text-success", className)}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path d={SEAL_RING_PATH} fill="currentColor" fillRule="evenodd" />
      <circle
        cx="50"
        cy="50"
        r={SEAL_INNER_RING.r}
        fill="none"
        stroke="currentColor"
        strokeWidth={SEAL_INNER_RING.strokeWidth}
      />
      <path
        d={SEAL_CHECK_PATH}
        fill="none"
        stroke="currentColor"
        strokeWidth={SEAL_CHECK_STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Mark + wordmark lockup used in top bars and the auth panel. */
export function BrandLockup({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <SealMark className="h-7 w-7 shrink-0" />
      <span className="font-serif text-xl font-bold tracking-tight text-foreground">{name}</span>
    </span>
  );
}
