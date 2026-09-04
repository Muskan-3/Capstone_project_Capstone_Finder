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
      </body>
    </html>
  );
}
