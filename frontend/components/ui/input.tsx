import { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent",
        className
      )}
      {...props}
    />
  );
}
