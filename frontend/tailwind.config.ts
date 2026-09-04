import type { Config } from "tailwindcss";

/**
 * Palette + type are declared once here (and mirrored as CSS variables in
 * globals.css). Components reference these tokens, never raw hex.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        "ink-soft": "var(--ink-soft)",
        parchment: "var(--parchment)",
        "parchment-raised": "var(--parchment-raised)",
        "tint-blue": "var(--tint-blue)",
        "tint-blue-soft": "var(--tint-blue-soft)",
        brass: "var(--brass)",
        "brass-soft": "var(--brass-soft)",
        "deep-teal": "var(--deep-teal)",
        "charcoal-text": "var(--charcoal-text)",
        hairline: "var(--hairline)",
        "ink-hairline": "var(--ink-hairline)",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "Cambria", "serif"],
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        card: "3px",
        panel: "2px",
      },
      maxWidth: {
        chart: "1240px",
      },
    },
  },
  plugins: [],
};

export default config;
