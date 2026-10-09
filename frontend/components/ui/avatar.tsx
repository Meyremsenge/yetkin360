import { cn } from "@/lib/utils";

/**
 * Brif §2.14: daire, kum zemin, 1px çizgi, içinde baş harfler Serif 500 mürekkep.
 * Hiçbir zaman fotoğraf — yalnız baş harfler.
 */
export function Avatar({
  name,
  size = 64,
  className = "",
}: {
  name: string;
  size?: number;
  className?: string;
}) {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  return (
    <div
      className={cn(
        "shrink-0 flex items-center justify-center rounded-full bg-sand border border-border font-serif text-foreground",
        className
      )}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      aria-hidden="true"
    >
      {initials || "?"}
    </div>
  );
}
