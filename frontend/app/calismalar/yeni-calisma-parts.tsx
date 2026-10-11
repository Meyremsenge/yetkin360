import type { ReactNode } from "react";
import type { Approver } from "@/lib/api/organizations";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const k = messages.kurulusSec;

/** Both screens of "Yeni çalışma" show where the student is: organization → details → tasks. */
export function NewEngagementSteps({ current }: { current: 1 | 2 }) {
  const steps = [k.stepOrg, k.stepDetails, k.stepTasks];
  return (
    <nav aria-label={k.stepsLabel}>
      <ol className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm sm:gap-x-3">
        {steps.map((label, index) => {
          const number = index + 1;
          const done = number < current;
          const active = number === current;
          return (
            <li key={label} className="flex items-center gap-3">
              {index > 0 ? <span aria-hidden="true" className="hidden h-px w-10 bg-border sm:block" /> : null}
              <span
                aria-current={active ? "step" : undefined}
                className={cn(
                  "inline-flex items-center gap-2",
                  active ? "font-medium text-foreground" : "text-muted-foreground"
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-full border font-mono text-xs",
                    done && "border-success bg-success text-background",
                    active && "border-success bg-success/10 text-success",
                    !done && !active && "border-border bg-card"
                  )}
                >
                  {done ? <CheckIcon /> : number}
                </span>
                {label}
                {active ? <span className="sr-only">{k.stepCurrent}</span> : null}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function CheckIcon({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2.2} aria-hidden="true">
      <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

type PersonWithHint = Pick<Approver, "display_name" | "email_hint"> & { unit?: string | null };

export function approverName(approver: PersonWithHint): string {
  return approver.display_name.trim() || k.approverUnnamed;
}

function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase("tr-TR"))
    .join("");
}

/** Name, unit and masked e-mail — the student sees which address of the organization approves. */
export function ApproverIdentity({ approver, aside }: { approver: PersonWithHint; aside?: ReactNode }) {
  const name = approverName(approver);
  return (
    <span className="flex min-w-0 items-center gap-3">
      <span
        aria-hidden="true"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sand font-serif text-sm font-semibold text-foreground"
      >
        {initials(approver.display_name) || "?"}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground">
          {name}
          {approver.unit ? <span className="font-normal text-muted-foreground"> · {approver.unit}</span> : null}
        </span>
        <span className="block truncate font-mono text-xs text-muted-foreground">{approver.email_hint}</span>
      </span>
      {aside}
    </span>
  );
}
