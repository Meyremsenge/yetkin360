import type { Config } from "tailwindcss";

// Legacy screens still use stock Tailwind scales (slate/red/green/amber/blue).
// Re-map them onto the paper-ink-seal palette so every screen shares one look
// without touching class names: slate → warm ink, red → brick, green → pine,
// amber/yellow → ochre, blue → pine (blue is not part of the palette).
const ink = {
  50: "#F8F6F2", 100: "#F0ECE6", 200: "#E3DDD4", 300: "#D2CABF", 400: "#A29A8F",
  500: "#7A736A", 600: "#625C55", 700: "#4A453F", 800: "#332F2B", 900: "#221F1B", 950: "#161412",
};
const brick = {
  50: "#FAF0EE", 100: "#F3DED9", 200: "#E8C2B9", 300: "#D89A8C", 400: "#C66F5D",
  500: "#B4503E", 600: "#A13B2B", 700: "#863022", 800: "#6B271B", 900: "#521E15", 950: "#36130D",
};
const pine = {
  50: "#ECF4F0", 100: "#D8E9E0", 200: "#B7D5C5", 300: "#8DBBA3", 400: "#5E9A7E",
  500: "#3B7560", 600: "#265445", 700: "#1F4639", 800: "#18372D", 900: "#122A22", 950: "#0B1B16",
};
const ochre = {
  50: "#FAF3E7", 100: "#F2E3C8", 200: "#E6CA98", 300: "#D6AB62", 400: "#C4913F",
  500: "#A9742A", 600: "#8F5A14", 700: "#784B10", 800: "#5F3B0D", 900: "#472C0A", 950: "#2E1C06",
};

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        primary: "hsl(var(--primary))",
        muted: "hsl(var(--muted))",
        sand: "hsl(var(--sand))",
        border: "hsl(var(--border))",
        destructive: "hsl(var(--destructive))",
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        "muted-foreground": "hsl(var(--ink-soft))",
        verified: "hsl(var(--success))",
        slate: ink,
        gray: ink,
        red: brick,
        green: pine,
        emerald: pine,
        blue: pine,
        amber: ochre,
        yellow: ochre,
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)"],
        serif: ["var(--font-source-serif)"],
        mono: ["var(--font-plex-mono)"],
      },
    },
  },
  plugins: [],
};

export default config;
