import type { Config } from "tailwindcss";

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
        border: "hsl(var(--border))",
        destructive: "hsl(var(--destructive))",
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        "muted-foreground": "hsl(var(--ink-soft))",
        verified: "hsl(var(--success))",
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
