import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("bg-card text-foreground border border-border rounded-lg p-6", className)}
      {...props}
    />
  );
}
