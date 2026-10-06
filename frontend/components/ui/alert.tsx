import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Alert({
  className = "",
  variant = "info",
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  variant?: "error" | "success" | "warning" | "info";
}) {
  const variantClasses: Record<string, string> = {
    error: "bg-destructive/10 text-destructive border-destructive/30",
    success: "bg-success/10 text-success border-success/30",
    warning: "bg-warning/10 text-warning border-warning/30",
    info: "bg-muted text-foreground border-border",
  };

  return (
    <div
      role="alert"
      aria-live={variant === "error" ? "assertive" : "polite"}
      className={cn("border rounded-md p-4", variantClasses[variant], className)}
      {...props}
    />
  );
}
