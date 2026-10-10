import { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Button({
  className = "",
  variant = "primary",
  size = "md",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "destructive" | "ghost";
  size?: "sm" | "md" | "lg";
}) {
  const variantClasses: Record<string, string> = {
    primary: "bg-success text-white",
    destructive: "bg-destructive text-white",
    secondary: "bg-muted text-foreground",
    ghost: "bg-transparent",
  };

  const hoverClasses: Record<string, string> = {
    primary: "hover:bg-success/90",
    destructive: "hover:bg-destructive/90",
    secondary: "hover:bg-muted/80",
    ghost: "hover:bg-muted",
  };

  const sizeClasses: Record<string, string> = {
    sm: "h-8 px-3 text-sm",
    md: "px-4 py-2 text-sm",
    lg: "h-12 px-6 text-base",
  };

  return (
    <button
      className={cn(
        "rounded-md font-medium",
        variantClasses[variant],
        hoverClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    />
  );
}
