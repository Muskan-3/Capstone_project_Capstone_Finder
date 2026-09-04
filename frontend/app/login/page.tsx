"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CompassMark } from "@/components/CompassMark";
import { TagInput } from "@/components/TagInput";
import { api, ApiError } from "@/lib/api";
import { profileStore, sessionStore } from "@/lib/store";
import type { StudentProfile } from "@/lib/types";

const SKILL_SUGGESTIONS = [
  "Python", "Qiskit", "PennyLane", "linear algebra", "machine learning", "PyTorch",
  "cryptography", "React", "TypeScript", "data visualization", "signal processing",
  "optimization", "cloud / DevOps", "C++",
];
const INTEREST_SUGGESTIONS = [
  "quantum machine learning", "variational circuits", "post-quantum cryptography",
  "optimization", "medical imaging", "cybersecurity", "sustainability", "finance",
  "AR / VR", "developer tools", "NLP", "computer vision",
];
const OUTCOMES = [
  "Research prototype / paper",
  "Deployable application",
  "Benchmark / evaluation study",
  "Simulation or dataset",
  "Not sure yet",
];
const COMFORT: { value: string; label: string; hint: string }[] = [
  { value: "exploring", label: "Exploring", hint: "new to most of this" },
  { value: "moderate", label: "Comfortable", hint: "have built a few things" },
  { value: "high", label: "Fluent", hint: "ship independently" },
];

const EMPTY: StudentProfile = {
  name: "",
  skills: [],
  interests: [],
  tech_comfort: "moderate",
  prior_projects: "",
  preferred_outcome: "",
};

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState<StudentProfile>(EMPTY);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<1 | 2>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existing, setExisting] = useState<{ name: string; studentId: number } | null>(null);

  useEffect(() => {
    const s = sessionStore.get();
    if (s) setExisting({ name: s.name, studentId: s.studentId });
    const saved = profileStore.get();
    if (saved) setForm({ ...EMPTY, ...saved });
  }, []);

  const set = <K extends keyof StudentProfile>(k: K, v: StudentProfile[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const canContinueStep1 = form.name.trim().length > 0 && email.trim().length > 3 && password.length >= 4;
  const canSubmit = form.skills.length > 0 || form.interests.length > 0;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await api.saveStudent(form);
      profileStore.set(saved);
      sessionStore.set({ studentId: saved.id, name: saved.name, email });
      router.push("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong signing you in.");
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* brand panel */}
      <div
        className="relative hidden flex-col justify-between overflow-hidden p-10 lg:flex"
        style={{ background: "var(--ink)", color: "var(--on-ink)" }}
      >
        <div
          className="gradient-pan pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(50% 45% at 20% 20%, var(--brass), transparent), radial-gradient(45% 40% at 85% 75%, var(--deep-teal), transparent)",
          }}
        />
        <div className="pointer-events-none absolute -right-24 -top-24 opacity-20">
          <CompassMark size={420} />
        </div>
        <div className="float-a pointer-events-none absolute left-14 top-40 hidden rounded-xl border px-3 py-2 backdrop-blur xl:block" style={{ borderColor: "var(--ink-hairline)", background: "rgba(255,255,255,0.06)" }}>
          <p className="text-[10px]" style={{ color: "var(--on-ink-dim)" }}>Real similarity</p>
          <p className="data-token text-sm" style={{ color: "var(--on-ink-accent)" }}>0.236 · strong</p>
        </div>
        <div className="float-b pointer-events-none absolute bottom-40 right-12 hidden rounded-xl border px-3 py-2 backdrop-blur xl:block" style={{ borderColor: "var(--ink-hairline)", background: "rgba(255,255,255,0.06)" }}>
          <p className="text-[10px]" style={{ color: "var(--on-ink-dim)" }}>Cited</p>
          <p className="data-token text-sm">ASAC-CAP-PROJ-528</p>
        </div>

        <Link href="/" className="relative flex items-center gap-2.5">
          <span style={{ color: "var(--on-ink-accent)" }}>
            <CompassMark size={26} />
          </span>
          <span className="font-display text-lg">Capstone Compass</span>
        </Link>
        <div className="relative max-w-sm">
          <h1 className="font-display text-3xl leading-tight">
            Sign in, then just tell it what you&rsquo;re into.
          </h1>
          <p className="mt-4 text-sm" style={{ color: "var(--on-ink-dim)" }}>
            One profile, one chat. Ask for ideas, push back on what comes back
            (&ldquo;avoid AR/VR&rdquo;, &ldquo;more optimization&rdquo;), and every answer still cites a
            real Project ID and a real similarity score.
          </p>
        </div>
        <p className="relative text-xs" style={{ color: "var(--on-ink-dim)" }}>
          Retrieval over the department&rsquo;s own catalogue. No hosted LLM, fully offline.
        </p>
      </div>

      {/* form panel */}
      <div className="flex items-center justify-center bg-parchment px-4 py-10 sm:px-6">
        <div className="w-full max-w-md">
          <div className="mb-6 flex items-center gap-2.5 lg:hidden">
            <span className="text-brass">
              <CompassMark size={24} />
            </span>
            <span className="font-display text-lg">Capstone Compass</span>
          </div>

          {existing && step === 1 && (
            <div className="chart-card mb-5 flex items-center justify-between gap-3 p-3.5 text-sm">
              <span>
                Continue as <span className="font-medium">{existing.name}</span>?
              </span>
              <button
                type="button"
                onClick={() => router.push("/chat")}
                className="btn btn-primary !py-1.5 text-xs"
              >
                Continue
              </button>
            </div>
          )}

          <div className="mb-4 flex items-center gap-1.5" aria-hidden>
            <span className="h-1.5 w-8 rounded-full" style={{ background: "var(--brass)" }} />
            <span
              className="h-1.5 w-8 rounded-full transition-colors"
              style={{ background: step === 2 ? "var(--brass)" : "var(--hairline)" }}
            />
          </div>

          <p className="text-sm text-brass">{step === 1 ? "Step 1 of 2 · Sign in" : "Step 2 of 2 · Your profile"}</p>
          <h1 className="mt-1 font-display text-2xl">
            {step === 1 ? "Welcome to Capstone Compass" : "What should it know about you?"}
          </h1>
          <p className="mt-2 text-sm text-charcoal-text/70">
            {step === 1
              ? "This is a lightweight local sign-in for the demo - no account verification happens server-side."
              : "Concrete skills and interests make for a sharper first answer in chat."}
          </p>

          <div key={step} className="chat-turn-in">
          {step === 1 ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setStep(2);
              }}
              className="mt-6 space-y-4"
            >
              <div>
                <label htmlFor="name" className="mb-1 block text-sm font-medium">
                  Full name
                </label>
                <input
                  id="name"
                  required
                  value={form.name}
                  onChange={(e) => set("name", e.target.value)}
                  className="chart-card w-full bg-parchment-raised px-3 py-2 text-sm outline-none"
                  placeholder="e.g. Priya Nair"
                />
              </div>
              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="chart-card w-full bg-parchment-raised px-3 py-2 text-sm outline-none"
                  placeholder="you@university.edu"
                />
              </div>
              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={4}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="chart-card w-full bg-parchment-raised px-3 py-2 text-sm outline-none"
                  placeholder="At least 4 characters"
                />
              </div>
              <button type="submit" className="btn btn-primary w-full" disabled={!canContinueStep1}>
                Continue
              </button>
            </form>
          ) : (
            <form onSubmit={submit} className="mt-6 space-y-5">
              <TagInput
                label="Skills"
                hint="Press Enter or comma to add."
                values={form.skills}
                onChange={(v) => set("skills", v)}
                placeholder="Python, linear algebra, React..."
                suggestions={SKILL_SUGGESTIONS}
              />
              <TagInput
                label="Interests"
                hint="Problem areas you want the project to be about."
                values={form.interests}
                onChange={(v) => set("interests", v)}
                placeholder="quantum machine learning, optimization..."
                suggestions={INTEREST_SUGGESTIONS}
              />
              <fieldset>
                <legend className="mb-2 text-sm font-medium">Technical comfort</legend>
                <div className="grid grid-cols-3 gap-2">
                  {COMFORT.map((c) => (
                    <label
                      key={c.value}
                      className={`chart-card cursor-pointer p-2.5 text-xs transition-colors ${
                        form.tech_comfort === c.value
                          ? "border-brass ring-1 ring-brass"
                          : "hover:border-brass/50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="tech_comfort"
                        value={c.value}
                        checked={form.tech_comfort === c.value}
                        onChange={(e) => set("tech_comfort", e.target.value)}
                        className="sr-only"
                      />
                      <span className="block font-medium">{c.label}</span>
                      <span className="block text-charcoal-text/55">{c.hint}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
              <div>
                <label htmlFor="prior" className="mb-1 block text-sm font-medium">
                  Prior projects <span className="font-normal text-charcoal-text/55">(optional)</span>
                </label>
                <textarea
                  id="prior"
                  rows={2}
                  value={form.prior_projects}
                  onChange={(e) => set("prior_projects", e.target.value)}
                  className="chart-card w-full bg-parchment-raised px-3 py-2 text-sm outline-none"
                  placeholder="A sentence or two about what you've built before."
                />
              </div>
              <div>
                <label htmlFor="outcome" className="mb-1 block text-sm font-medium">
                  Preferred outcome
                </label>
                <select
                  id="outcome"
                  value={form.preferred_outcome}
                  onChange={(e) => set("preferred_outcome", e.target.value)}
                  className="chart-card w-full bg-parchment-raised px-3 py-2 text-sm outline-none"
                >
                  <option value="">No preference</option>
                  {OUTCOMES.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              </div>

              {error && (
                <p role="alert" className="chart-card border-l-2 border-l-deep-teal p-3 text-sm">
                  {error}
                </p>
              )}

              <div className="flex items-center gap-3 pt-1">
                <button type="button" onClick={() => setStep(1)} className="btn btn-ghost">
                  Back
                </button>
                <button type="submit" className="btn btn-primary flex-1" disabled={!canSubmit || busy}>
                  {busy ? "Signing in..." : "Start chatting"}
                </button>
              </div>
              {!canSubmit && (
                <p className="text-xs text-charcoal-text/55">
                  Add at least one skill or interest to continue.
                </p>
              )}
            </form>
          )}
          </div>
        </div>
      </div>
    </div>
  );
}
