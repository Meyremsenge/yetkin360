import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className = "",
  variant = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success" | "error" | "warning";
}) {
  const variantClasses: Record<string, string> = {
    default: "bg-muted text-foreground",
    success: "bg-success/10 text-success",
    error: "bg-destructive/10 text-destructive",
    warning: "bg-warning/10 text-warning",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}
