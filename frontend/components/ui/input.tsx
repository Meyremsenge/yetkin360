import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function Input({
  className = "",
  ...props
}: ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "block w-full h-10 px-3 py-2 border border-border bg-card rounded-md text-sm text-foreground placeholder:text-muted-foreground/70 transition-colors hover:border-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-success/25 focus:border-success disabled:bg-muted",
        className
      )}
      {...props}
    />
  );
}
