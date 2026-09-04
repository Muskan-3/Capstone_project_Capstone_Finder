import Link from "next/link";
import { CompassMark } from "./CompassMark";

export function SiteFooter() {
  return (
    <footer style={{ background: "var(--ink)", color: "var(--on-ink)" }}>
      <div className="mx-auto max-w-chart px-4 py-14 sm:px-6">
        <div className="grid gap-10 sm:grid-cols-2 md:grid-cols-4">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2.5">
              <span style={{ color: "var(--on-ink-accent)" }}>
                <CompassMark size={22} />
              </span>
              <span className="font-display text-lg">Capstone Compass</span>
            </div>
            <p className="mt-3 max-w-xs text-sm" style={{ color: "var(--on-ink-dim)" }}>
              A wayfinding chat for final-year students - built on your department&rsquo;s real
              catalogue, running entirely offline on classical ML. No hosted LLM, no invented
              statements.
            </p>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--on-ink-accent)" }}>
              Product
            </p>
            <ul className="mt-3 space-y-2 text-sm" style={{ color: "var(--on-ink-dim)" }}>
              <li>
                <Link href="/login" className="hover:text-white">Get started</Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-white">How it works</Link>
              </li>
              <li>
                <Link href="/#features" className="hover:text-white">Features</Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--on-ink-accent)" }}>
              Staff
            </p>
            <ul className="mt-3 space-y-2 text-sm" style={{ color: "var(--on-ink-dim)" }}>
              <li>
                <Link href="/admin" className="hover:text-white">Faculty &amp; admin portal</Link>
              </li>
            </ul>
          </div>
        </div>

        <div
          className="mt-12 flex flex-col gap-2 border-t pt-6 text-xs sm:flex-row sm:items-center sm:justify-between"
          style={{ borderColor: "var(--ink-hairline)", color: "var(--on-ink-dim)" }}
        >
          <p>© {new Date().getFullYear()} Capstone Compass. Retrieval + adaptation, not generative AI.</p>
          <p>Photography via Unsplash.</p>
        </div>
      </div>
    </footer>
  );
}
