import Link from "next/link";
import { CompassMark } from "@/components/CompassMark";

const STAGES = [
  {
    bearing: "N",
    head: "Chart your position",
    body: "Your skills, interests and prior work become a point in the same vocabulary space as every problem statement in the catalogue.",
  },
  {
    bearing: "E",
    head: "Take a bearing",
    body: "We measure how close you sit to each domain cluster. If nothing is close enough, we say so plainly rather than pointing you somewhere wrong.",
  },
  {
    bearing: "S",
    head: "Plot the nearest routes",
    body: "Within the matched domain, statements are ranked by real cosine similarity, spread for variety, and shown with the score that put them there.",
  },
  {
    bearing: "W",
    head: "Adjust course",
    body: "Refine in plain language - “more web-based”, “avoid AR/VR” - and the ranking re-computes against the same catalogue.",
  },
];

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-chart px-4 sm:px-6">
      <section className="grid gap-10 py-14 md:grid-cols-[1.15fr_0.85fr] md:items-center md:py-20">
        <div>
          <p className="mb-4 flex items-center gap-2 text-sm text-deep-teal">
            <CompassMark size={18} />
            Grounded &middot; personalized &middot; transparent
          </p>
          <h1 className="font-display text-4xl leading-[1.1] sm:text-5xl">
            Find the capstone problem statement that actually fits your bearing.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-charcoal-text/80">
            Capstone Compass is a wayfinding instrument for final-year students. It searches the
            department&rsquo;s own catalogue of problem statements &mdash; not the open web, not a
            hosted model &mdash; and charts the ones closest to what you already know and want to
            build.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/onboarding" className="btn btn-primary">
              Chart my profile
            </Link>
            <Link href="/about" className="btn btn-ghost">
              How it works
            </Link>
          </div>
        </div>

        <div className="relative flex items-center justify-center">
          <div style={{ color: "var(--deep-teal)", opacity: 0.55 }}>
            <CompassMark size={260} />
          </div>
        </div>
      </section>

      <section className="chart-card chart-card--primary p-5 sm:p-6">
        <h2 className="font-display text-xl">What this tool will and won&rsquo;t claim</h2>
        <p className="mt-3 max-w-3xl text-charcoal-text/80">
          Every recommendation cites a real Project ID you can look up, and shows its real
          similarity score &mdash; there is no &ldquo;perfect match&rdquo;. The current catalogue is
          heavily weighted toward quantum-computing topics, so if your interests sit elsewhere the
          tool will tell you there isn&rsquo;t enough data yet instead of forcing a weak match.
          Recommendation text is the real problem statement, lightly framed around your profile;
          nothing is invented. Faculty matching is built but switched off until real supervisor
          preferences are entered.
        </p>
      </section>

      <section className="py-14">
        <h2 className="font-display text-2xl">The four bearings</h2>
        <div className="mt-6 grid gap-px overflow-hidden rounded-card border border-hairline bg-hairline sm:grid-cols-2">
          {STAGES.map((s) => (
            <div key={s.bearing} className="bg-parchment-raised p-5">
              <div className="flex items-baseline gap-3">
                <span className="data-token text-deep-teal">{s.bearing}</span>
                <h3 className="font-display text-lg">{s.head}</h3>
              </div>
              <p className="mt-2 text-sm text-charcoal-text/75">{s.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
