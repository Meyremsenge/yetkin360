/**
 * WCAG contrast ratio calculator for HSL color strings.
 * Used to verify that token color pairs meet accessibility requirements.
 */

/**
 * Parse HSL string and convert to RGB.
 *
 * @param hsl - HSL color string in format "H S% L%"
 *            (e.g., "30 12% 12%", "0 0% 100%")
 * @returns RGB object with r, g, b in 0-255 range
 * @throws {Error} if HSL format is invalid or values are not numeric
 */
function hslToRgb(hsl: string): { r: number; g: number; b: number } {
  // Trim and split by whitespace
  const parts = hsl.trim().split(/\s+/);

  if (parts.length !== 3) {
    throw new Error(
      `Invalid HSL format: expected "H S% L%", got "${hsl}"`
    );
  }

  const h = parseFloat(parts[0]);
  const s = parseFloat(parts[1].replace("%", ""));
  const l = parseFloat(parts[2].replace("%", ""));

  // Validate that all values are valid numbers
  if (isNaN(h) || isNaN(s) || isNaN(l)) {
    throw new Error(
      `Invalid HSL format: could not parse numbers from "${hsl}"`
    );
  }

  // Normalize saturation and lightness to 0-1 range
  const sNorm = s / 100;
  const lNorm = l / 100;

  // Calculate chroma and intermediate values (standard CSS HSL to RGB)
  const c = (1 - Math.abs(2 * lNorm - 1)) * sNorm;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = lNorm - c / 2;

  let r1, g1, b1;

  const h60 = h / 60;
  if (h60 < 1) {
    r1 = c;
    g1 = x;
    b1 = 0;
  } else if (h60 < 2) {
    r1 = x;
    g1 = c;
    b1 = 0;
  } else if (h60 < 3) {
    r1 = 0;
    g1 = c;
    b1 = x;
  } else if (h60 < 4) {
    r1 = 0;
    g1 = x;
    b1 = c;
  } else if (h60 < 5) {
    r1 = x;
    g1 = 0;
    b1 = c;
  } else {
    r1 = c;
    g1 = 0;
    b1 = x;
  }

  return {
    r: Math.round((r1 + m) * 255),
    g: Math.round((g1 + m) * 255),
    b: Math.round((b1 + m) * 255),
  };
}

/**
 * Calculate relative luminance according to WCAG formula.
 *
 * @param rgb - RGB object with r, g, b in 0-255 range
 * @returns Relative luminance value (0-1)
 */
function relativeLuminance(rgb: { r: number; g: number; b: number }): number {
  // Normalize RGB to 0-1 range
  let r = rgb.r / 255;
  let g = rgb.g / 255;
  let b = rgb.b / 255;

  // Apply gamma correction (WCAG standard)
  const adjust = (c: number) => {
    if (c <= 0.03928) {
      return c / 12.92;
    }
    return Math.pow((c + 0.055) / 1.055, 2.4);
  };

  r = adjust(r);
  g = adjust(g);
  b = adjust(b);

  // Calculate relative luminance
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Calculate WCAG contrast ratio between two HSL colors.
 *
 * @param hsl1 - First HSL color string in format "H S% L%"
 * @param hsl2 - Second HSL color string in format "H S% L%"
 * @returns Contrast ratio (higher = more contrast)
 * @throws {Error} if either HSL string is invalid
 *
 * Formula: (L_lighter + 0.05) / (L_darker + 0.05)
 * WCAG AA threshold: >= 4.5:1
 */
export function contrastRatio(hsl1: string, hsl2: string): number {
  const rgb1 = hslToRgb(hsl1);
  const rgb2 = hslToRgb(hsl2);

  const l1 = relativeLuminance(rgb1);
  const l2 = relativeLuminance(rgb2);

  // Determine which luminance is lighter
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  // WCAG contrast formula
  return (lighter + 0.05) / (darker + 0.05);
}
