import { cn } from "@/lib/utils";

const sizeClasses = {
  sm: { circle: "h-5 w-5", icon: "h-3 w-3" },
  md: { circle: "h-16 w-16", icon: "h-8 w-8" },
  lg: {
    circle: "h-24 w-24 -rotate-[4deg] outline outline-1 outline-offset-4 outline-success",
    icon: "h-12 w-12",
  },
} as const;

export function VerifiedSeal({
  name,
  issuedAt,
  registryNo,
  size = "md",
  label,
}: {
  name?: string;
  issuedAt?: string;
  registryNo?: string;
  size?: "sm" | "md" | "lg";
  label?: string;
}) {
  const classes = sizeClasses[size];
  return (
    <div data-testid="verified-seal" className="flex flex-col items-center gap-4 text-center">
      <span
        role={label ? "img" : undefined}
        aria-label={label}
        className={cn(
          "flex items-center justify-center rounded-full bg-success text-background",
          classes.circle
        )}
      >
        <svg
          viewBox="0 0 24 24"
          className={classes.icon}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path d="M5 12l5 5L20 7" />
        </svg>
      </span>
      {name ? <p className="font-serif text-2xl">{name}</p> : null}
      {issuedAt ? <p className="font-mono text-sm">{issuedAt}</p> : null}
      {registryNo ? <p className="font-mono text-sm">{registryNo}</p> : null}
    </div>
  );
}
