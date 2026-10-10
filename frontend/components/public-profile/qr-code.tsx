import { useMemo } from "react";
import qrcode from "qrcode-generator";
import { cn } from "@/lib/utils";

/**
 * QR code drawn as a single SVG path from the encoder's module matrix —
 * no generated markup is injected (no dangerouslySetInnerHTML).
 */
export function QrCode({ value, label, className }: { value: string; label: string; className?: string }) {
  const { size, path } = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(value);
    qr.make();
    const count = qr.getModuleCount();
    let d = "";
    for (let row = 0; row < count; row++) {
      for (let col = 0; col < count; col++) {
        if (qr.isDark(row, col)) d += `M${col + 2} ${row + 2}h1v1h-1z`;
      }
    }
    return { size: count + 4, path: d };
  }, [value]);

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={label}
      shapeRendering="crispEdges"
      className={cn("bg-white text-foreground", className)}
    >
      <path d={path} fill="currentColor" />
    </svg>
  );
}
