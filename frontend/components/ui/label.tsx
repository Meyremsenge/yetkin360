import { LabelHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Label({
  className = "",
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("block text-sm font-medium text-foreground mb-1.5", className)}
      {...props}
    />
  );
}
