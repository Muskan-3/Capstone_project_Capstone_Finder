import type { Metadata } from "next";
import "./globals.css";
import { fraunces, inter, jetbrainsMono } from "./fonts";
import { SiteNav } from "@/components/SiteNav";

export const metadata: Metadata = {
  title: "Capstone Compass",
  description:
    "A wayfinding instrument for capstone problem statements. Grounded, personalized, transparent - TF-IDF retrieval over the department's own catalogue, no hosted LLM.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen antialiased">
        <SiteNav />
        <main>{children}</main>
        <footer className="mx-auto max-w-chart px-4 py-10 text-xs text-charcoal-text/55 sm:px-6">
          <p>
            Capstone Compass runs fully offline on classical ML (TF-IDF + KMeans + cosine
            similarity). Recommendations are retrieval and adaptation over the local corpus, not
            generative. Faculty matching is inactive until real preference data is collected.
          </p>
        </footer>
      </body>
    </html>
  );
}
