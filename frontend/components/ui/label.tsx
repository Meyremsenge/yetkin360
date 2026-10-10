import { LabelHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Label({
  className = "",
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("block text-sm font-medium text-slate-700 mb-1", className)}
      {...props}
    />
  );
}
