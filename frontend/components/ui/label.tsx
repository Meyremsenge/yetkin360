import { LabelHTMLAttributes } from "react";

export function Label({
  className = "",
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={`block text-sm font-medium text-slate-700 mb-1 ${className}`}
      {...props}
    />
  );
}
