import localFont from "next/font/local";

/**
 * Fonts are vendored as .woff2 in /public/fonts and loaded from disk at build
 * time - no network request to Google Fonts, ever. Fraunces + Inter here are the
 * variable builds (latin subset).
 */
export const fraunces = localFont({
  src: [{ path: "../public/fonts/fraunces-latin.woff2", weight: "400 700", style: "normal" }],
  variable: "--font-fraunces",
  display: "swap",
  fallback: ["Georgia", "Cambria", "Times New Roman", "serif"],
});

export const inter = localFont({
  src: [{ path: "../public/fonts/inter-latin.woff2", weight: "400 700", style: "normal" }],
  variable: "--font-inter",
  display: "swap",
  fallback: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
});

export const jetbrainsMono = localFont({
  src: [{ path: "../public/fonts/jetbrainsmono-latin.woff2", weight: "400 500", style: "normal" }],
  variable: "--font-jetbrains",
  display: "swap",
  fallback: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
});
