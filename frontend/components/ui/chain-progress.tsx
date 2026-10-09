import { cn } from "@/lib/utils";

export function ChainProgress({
  steps,
}: {
  steps: { label: string; completed: boolean }[];
}) {
  return (
    <ol className="flex flex-col gap-6 md:flex-row md:gap-0">
      {steps.map((step, index) => (
        <li
          key={step.label}
          className="flex items-center gap-3 md:flex-1 md:flex-col md:items-start"
        >
          <span
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border font-mono text-sm transition-colors motion-reduce:transition-none",
              step.completed && "border-success bg-success text-background"
            )}
          >
            {index + 1}
          </span>
          <span
            className={cn(
              "font-serif text-lg",
              step.completed && "text-success"
            )}
          >
            {step.label}
          </span>
        </li>
      ))}
    </ol>
  );
}
