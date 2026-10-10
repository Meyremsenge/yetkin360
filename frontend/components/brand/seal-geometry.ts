/**
 * Single source of truth for the Yetkin360 seal mark, in a 100×100 box.
 * Used by the SVG logo, the favicon and the particle scene (via Path2D),
 * so all three always draw the exact same shape.
 */

const SCALLOPS = 28;
const OUTER_RADIUS = 47;
const SCALLOP_DEPTH = 1.7;
const RING_INNER_RADIUS = 39;

function circlePath(r: number): string {
  // Two arcs: an SVG/Path2D circle that works with the even-odd fill rule.
  return `M ${50 - r} 50 a ${r} ${r} 0 1 0 ${2 * r} 0 a ${r} ${r} 0 1 0 ${-2 * r} 0 Z`;
}

function scallopedPath(): string {
  const steps = SCALLOPS * 8;
  const points: string[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const angle = (i / steps) * Math.PI * 2;
    const r = OUTER_RADIUS - SCALLOP_DEPTH * (1 - Math.cos(angle * SCALLOPS)) * 0.5;
    const x = 50 + r * Math.cos(angle);
    const y = 50 + r * Math.sin(angle);
    points.push(`${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  return `${points.join(" ")} Z`;
}

/** Scalloped outer band — fill with `fill-rule="evenodd"`. */
export const SEAL_RING_PATH = `${scallopedPath()} ${circlePath(RING_INNER_RADIUS)}`;

/** Thin inner ring — stroke only. */
export const SEAL_INNER_RING = { r: 34, strokeWidth: 1.8 } as const;

/** Check mark — stroke only, round caps/joins. */
export const SEAL_CHECK_PATH = "M 32 51 L 44.5 63 L 68.5 38";
export const SEAL_CHECK_STROKE = 7;
