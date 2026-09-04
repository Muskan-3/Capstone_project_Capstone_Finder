import Link from "next/link";
import Image from "next/image";
import { CompassMark } from "@/components/CompassMark";
import { ScrollReveal } from "@/components/ScrollReveal";
import { SiteFooter } from "@/components/SiteFooter";

const STATS = [
  { value: "200+", label: "real problem statements" },
  { value: "6", label: "domain clusters, auto-discovered" },
  { value: "0", label: "hosted LLM calls" },
  { value: "100%", label: "offline after install" },
];

const FEATURES = [
  {
    icon: <IconTarget />,
    title: "Grounded, not generated",
    body: "Every reply is a real statement from your department's catalogue, adapted around your skills - never invented.",
  },
  {
    icon: <IconGauge />,
    title: "Honest confidence",
    body: "Every match ships with its real cosine similarity. No domain fit yet? It says so, instead of forcing a weak match.",
  },
  {
    icon: <IconLayers />,
    title: "Explainable, always",
    body: "Open “Explain this match” on any card to see exactly which of your skills and interests drove the ranking.",
  },
  {
    icon: <IconChat />,
    title: "Just chat about it",
    body: "No forms, no filters to configure. Describe what you're into, push back in plain language, get re-ranked instantly.",
  },
];

const COMPARISON = [
  { label: "Sources its answers from", them: "Whatever it learned in training", us: "Your department's real catalogue" },
  { label: "Shows a similarity score", them: false, us: true },
  { label: "Cites a real Project ID", them: false, us: true },
  { label: "Says “not enough data” when true", them: false, us: true },
  { label: "Runs without an internet connection", them: false, us: true },
  { label: "Can invent a project that doesn't exist", them: true, us: false },
];

const FAQS = [
  {
    q: "Is this powered by ChatGPT or another LLM?",
    a: "No. There is no hosted model anywhere in the pipeline. Matching runs on TF-IDF vectors, KMeans clustering, and cosine similarity - all classical, all computed locally from your department's own statements.",
  },
  {
    q: "What happens if my interests don't fit the catalogue?",
    a: "You get told, plainly. If nothing clears the confidence threshold, the chat says so and shows the closest available statements labelled as weak leads with their real scores - never a forced match dressed up as a good one.",
  },
  {
    q: "Where does my profile data go?",
    a: "Into the department's own database via the app's backend - not a third party, not a training set. The current build uses a local session; a Supabase-backed account system is planned.",
  },
  {
    q: "Can I change my mind mid-chat?",
    a: "Yes - that's the point. Reply in plain language (“avoid AR/VR”, “more optimization”, “something web-based instead”) and the ranking recomputes around your new message.",
  },
  {
    q: "Do faculty see or manage the catalogue?",
    a: "Yes, through a separate portal that mirrors the department's existing manual review process - flagged rows, batch uploads, and model retraining, kept out of the student-facing chat.",
  },
];

const STAGES = [
  {
    bearing: "N",
    head: "Chart your position",
    body: "Sign in once and your skills, interests and prior work become a point in the same vocabulary space as every problem statement.",
  },
  {
    bearing: "E",
    head: "Take a bearing",
    body: "We measure how close you sit to each domain cluster. Not close enough anywhere? You'll be told plainly, not pointed somewhere wrong.",
  },
  {
    bearing: "S",
    head: "Plot the nearest routes",
    body: "Inside the matched domain, statements are ranked by real cosine similarity and spread for variety - never five versions of one idea.",
  },
  {
    bearing: "W",
    head: "Adjust course",
    body: "Reply in plain language - “more web-based”, “avoid AR/VR” - and the whole ranking recomputes around your next message.",
  },
];

export default function LandingPage() {
  return (
    <div>
      {/* ============================== HERO ============================== */}
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 -z-10 gradient-pan opacity-70"
          style={{
            background:
              "radial-gradient(60% 55% at 15% 15%, var(--brass-soft), transparent), radial-gradient(55% 50% at 90% 25%, var(--deep-teal-soft), transparent)",
          }}
        />
        <div className="mx-auto grid max-w-chart gap-10 px-4 py-16 sm:px-6 sm:py-20 md:grid-cols-[1.05fr_0.95fr] md:items-center md:py-28">
          <div>
            <p className="mb-4 flex items-center gap-2 text-sm font-medium" style={{ color: "var(--deep-teal)" }}>
              <CompassMark size={18} />
              Grounded &middot; personalized &middot; transparent
            </p>
            <h1 className="font-display text-4xl leading-[1.08] sm:text-5xl md:text-[3.3rem]">
              Your capstone idea is in there somewhere.{" "}
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: "linear-gradient(90deg, var(--brass), var(--deep-teal))" }}
              >
                Let&rsquo;s go find it.
              </span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-charcoal-text/75">
              Capstone Compass is a chat-first way to search your department&rsquo;s own catalogue of
              problem statements &mdash; not the open web, not a hosted model. Tell it what you know
              and what you&rsquo;re into, and it charts the closest real matches, scored and cited.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/login" className="btn btn-primary px-6 py-3 text-base shadow-lg shadow-[color:var(--brass-soft)]">
                Log in &amp; start chatting
              </Link>
              <a href="#features" className="btn btn-ghost px-6 py-3 text-base">
                See how it works
              </a>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-charcoal-text/55">
              <span>No hosted LLM</span>
              <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
              <span>Runs fully offline</span>
              <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
              <span>Every score is real</span>
            </div>
          </div>

          <div className="relative">
            <div className="float-a relative mx-auto aspect-[4/3] w-full max-w-md overflow-hidden rounded-2xl shadow-2xl">
              <Image
                src="/images/hero-graduation.jpg"
                alt="Graduates celebrating, caps thrown in the air"
                fill
                priority
                sizes="(min-width: 768px) 480px, 90vw"
                className="object-cover"
              />
              <div
                className="absolute inset-0"
                style={{ background: "linear-gradient(200deg, rgba(47,111,237,0.25), rgba(124,92,252,0.15) 60%, transparent)" }}
              />
            </div>
            <div className="float-b absolute -left-4 -top-4 hidden rounded-xl border border-hairline bg-parchment-raised px-3 py-2 shadow-lg sm:block">
              <p className="text-[10px] text-charcoal-text/55">Routed with confidence</p>
              <p className="data-token text-sm text-brass">0.207 · strong</p>
            </div>
            <div className="float-b absolute -bottom-5 -right-3 hidden rounded-xl border border-hairline bg-parchment-raised px-3 py-2 shadow-lg sm:block">
              <p className="text-[10px] text-charcoal-text/55">Project ID</p>
              <p className="data-token text-sm">ASAC-CAP-PROJ-528</p>
            </div>
          </div>
        </div>
      </section>

      {/* ============================== STATS ============================== */}
      <section className="border-y border-hairline bg-tint-blue">
        <div className="mx-auto grid max-w-chart grid-cols-2 gap-6 px-4 py-10 sm:px-6 md:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="text-center md:text-left">
              <p className="font-display text-3xl" style={{ color: "var(--brass)" }}>
                {s.value}
              </p>
              <p className="mt-1 text-xs text-charcoal-text/60">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ============================== FEATURES ============================== */}
      <section id="features" className="mx-auto max-w-chart px-4 py-20 sm:px-6">
        <ScrollReveal>
          <p className="text-sm font-medium" style={{ color: "var(--deep-teal)" }}>
            Why it&rsquo;s different
          </p>
          <h2 className="mt-1 font-display text-3xl">Not another generic recommender</h2>
        </ScrollReveal>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f, i) => (
            <ScrollReveal key={f.title} delay={i * 80}>
              <div className="group h-full rounded-2xl border border-hairline bg-parchment-raised p-5 transition-all hover:-translate-y-1 hover:shadow-xl">
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-xl text-white transition-transform group-hover:scale-105"
                  style={{ background: "linear-gradient(135deg, var(--brass), var(--deep-teal))" }}
                >
                  {f.icon}
                </div>
                <h3 className="mt-4 font-display text-lg">{f.title}</h3>
                <p className="mt-1.5 text-sm text-charcoal-text/70">{f.body}</p>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </section>

      {/* ============================== SOCIAL / PHOTO SECTION ============================== */}
      <section className="mx-auto max-w-chart px-4 py-10 sm:px-6 md:py-16">
        <div className="grid items-center gap-10 md:grid-cols-2">
          <ScrollReveal>
            <p className="text-sm font-medium" style={{ color: "var(--deep-teal)" }}>
              Built for the room you're already in
            </p>
            <h2 className="mt-1 font-display text-3xl">
              The same late-night library energy, minus the guesswork.
            </h2>
            <p className="mt-4 text-charcoal-text/75">
              You already know the drill: a table, a few laptops, and a group chat full of half-formed
              project ideas. Capstone Compass doesn&rsquo;t replace that conversation - it gives it
              somewhere real to start, grounded in statements your own department has actually
              published.
            </p>
            <ul className="mt-5 space-y-2 text-sm text-charcoal-text/75">
              <li className="flex gap-2">
                <Dot /> Works for a solo search or a team brainstorm
              </li>
              <li className="flex gap-2">
                <Dot /> Every suggestion is something a supervisor can actually assign
              </li>
              <li className="flex gap-2">
                <Dot /> Keeps a running chat, not a one-shot quiz
              </li>
            </ul>
          </ScrollReveal>

          <ScrollReveal delay={120}>
            <div className="grid grid-cols-2 gap-3">
              <div className="relative col-span-2 aspect-[16/10] overflow-hidden rounded-2xl shadow-lg">
                <Image
                  src="/images/students-laptops.jpg"
                  alt="Three students laughing together while working on laptops"
                  fill
                  sizes="(min-width: 768px) 420px, 90vw"
                  className="object-cover"
                  loading="lazy"
                />
              </div>
              <div className="relative aspect-square overflow-hidden rounded-2xl shadow-lg">
                <Image
                  src="/images/study-group-library.jpg"
                  alt="A study group gathered around a laptop in a library"
                  fill
                  sizes="(min-width: 768px) 200px, 45vw"
                  className="object-cover"
                  loading="lazy"
                />
              </div>
              <div className="relative aspect-square overflow-hidden rounded-2xl shadow-lg">
                <Image
                  src="/images/overhead-laptops.jpg"
                  alt="Overhead view of several laptops and coding notes on a desk"
                  fill
                  sizes="(min-width: 768px) 200px, 45vw"
                  className="object-cover"
                  loading="lazy"
                />
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* ============================== HOW IT WORKS ============================== */}
      <section className="bg-tint-blue py-20">
        <div className="mx-auto max-w-chart px-4 sm:px-6">
          <ScrollReveal>
            <p className="text-sm font-medium" style={{ color: "var(--deep-teal)" }}>
              The mechanism
            </p>
            <h2 className="mt-1 font-display text-3xl">Four bearings, one conversation</h2>
          </ScrollReveal>
          <div className="mt-10 grid gap-px overflow-hidden rounded-2xl border border-hairline bg-hairline sm:grid-cols-2 lg:grid-cols-4">
            {STAGES.map((s, i) => (
              <ScrollReveal key={s.bearing} delay={i * 80} className="h-full">
                <div className="h-full bg-parchment-raised p-6">
                  <span
                    className="data-token flex h-8 w-8 items-center justify-center rounded-lg text-sm text-white"
                    style={{ background: "var(--brass)" }}
                  >
                    {s.bearing}
                  </span>
                  <h3 className="mt-4 font-display text-lg">{s.head}</h3>
                  <p className="mt-2 text-sm text-charcoal-text/70">{s.body}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
          <ScrollReveal delay={200}>
            <p className="mt-6 text-sm text-charcoal-text/60">
              Curious about the machinery - TF-IDF, KMeans, cosine ranking?{" "}
              <Link href="/about" className="link-teal">
                Read the full breakdown
              </Link>
              .
            </p>
          </ScrollReveal>
        </div>
      </section>

      {/* ============================== COMPARISON ============================== */}
      <section className="mx-auto max-w-chart px-4 py-20 sm:px-6">
        <ScrollReveal className="text-center">
          <p className="text-sm font-medium" style={{ color: "var(--deep-teal)" }}>
            The honest comparison
          </p>
          <h2 className="mt-1 font-display text-3xl">Not the same as just asking a chatbot</h2>
          <p className="mx-auto mt-3 max-w-xl text-charcoal-text/70">
            A general-purpose chatbot will happily invent a plausible-sounding project. Here&rsquo;s
            what actually differs when the answer has to be real.
          </p>
        </ScrollReveal>

        <ScrollReveal delay={100}>
          <div className="mt-10 overflow-hidden rounded-2xl border border-hairline">
            <div className="grid grid-cols-[1.4fr_1fr_1fr] bg-tint-blue text-sm font-medium">
              <div className="px-4 py-3 sm:px-6">&nbsp;</div>
              <div className="px-4 py-3 text-center text-charcoal-text/60 sm:px-6">Generic chatbot</div>
              <div className="px-4 py-3 text-center sm:px-6" style={{ color: "var(--brass)" }}>
                Capstone&nbsp;Compass
              </div>
            </div>
            {COMPARISON.map((row, i) => (
              <div
                key={row.label}
                className={`grid grid-cols-[1.4fr_1fr_1fr] items-center text-sm ${i % 2 ? "bg-parchment" : "bg-parchment-raised"}`}
              >
                <div className="px-4 py-3.5 sm:px-6">{row.label}</div>
                <div className="px-4 py-3.5 text-center sm:px-6">
                  <Cell value={row.them} />
                </div>
                <div className="px-4 py-3.5 text-center sm:px-6">
                  <Cell value={row.us} />
                </div>
              </div>
            ))}
          </div>
        </ScrollReveal>
      </section>

      {/* ============================== FAQ ============================== */}
      <section className="bg-tint-blue py-20">
        <div className="mx-auto max-w-3xl px-4 sm:px-6">
          <ScrollReveal className="text-center">
            <p className="text-sm font-medium" style={{ color: "var(--deep-teal)" }}>
              Questions
            </p>
            <h2 className="mt-1 font-display text-3xl">Before you sign in</h2>
          </ScrollReveal>

          <div className="mt-8 space-y-3">
            {FAQS.map((f, i) => (
              <ScrollReveal key={f.q} delay={i * 60}>
                <details className="group rounded-2xl border border-hairline bg-parchment-raised px-5 py-4 open:shadow-md">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                    {f.q}
                    <span
                      className="shrink-0 text-lg text-charcoal-text/40 transition-transform group-open:rotate-45"
                      aria-hidden
                    >
                      +
                    </span>
                  </summary>
                  <p className="mt-2.5 text-sm text-charcoal-text/70">{f.a}</p>
                </details>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* ============================== CTA BANNER ============================== */}
      <section className="mx-auto max-w-chart px-4 py-20 sm:px-6">
        <ScrollReveal>
          <div
            className="relative overflow-hidden rounded-3xl px-6 py-14 text-center sm:px-16"
            style={{ background: "linear-gradient(120deg, var(--brass), var(--deep-teal))" }}
          >
            <div className="pointer-events-none absolute -left-10 -top-10 h-40 w-40 rounded-full bg-white/10 float-a" />
            <div className="pointer-events-none absolute -bottom-12 -right-6 h-52 w-52 rounded-full bg-white/10 float-b" />
            <h2 className="relative font-display text-3xl text-white sm:text-4xl">
              Stop scrolling spreadsheets of problem statements.
            </h2>
            <p className="relative mx-auto mt-3 max-w-lg text-white/85">
              One sign-in, one chat, real matches with real scores - built for the deadline you
              actually have.
            </p>
            <Link
              href="/login"
              className="relative mt-7 inline-flex items-center justify-center rounded-sm bg-white px-7 py-3 text-base font-medium text-charcoal-text transition-transform hover:scale-[1.03]"
            >
              Log in &amp; start chatting
            </Link>
          </div>
        </ScrollReveal>
      </section>

      <SiteFooter />
    </div>
  );
}

function Cell({ value }: { value: boolean | string }) {
  if (typeof value === "string") {
    return <span className="text-xs text-charcoal-text/70">{value}</span>;
  }
  return value ? (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full text-white" style={{ background: "var(--brass)" }} aria-label="Yes">
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
        <path d="M2 6.2 4.8 9 10 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  ) : (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-charcoal-text/10 text-charcoal-text/40" aria-label="No">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
        <path d="M1 1l8 8M9 1 1 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    </span>
  );
}

function Dot() {
  return <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: "var(--brass)" }} />;
}

function IconTarget() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="4.5" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" />
    </svg>
  );
}
function IconGauge() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 16a8 8 0 1 1 16 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M12 16 16 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function IconLayers() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 4 21 9l-9 5-9-5 9-5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M3 14l9 5 9-5" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
function IconChat() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 5h16v10H8l-4 4V5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}
