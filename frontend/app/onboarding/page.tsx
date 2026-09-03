"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TagInput } from "@/components/TagInput";
import { api, ApiError } from "@/lib/api";
import { profileStore } from "@/lib/store";
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

export default function OnboardingPage() {
  const router = useRouter();
  const [form, setForm] = useState<StudentProfile>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const saved = profileStore.get();
    if (saved) setForm({ ...EMPTY, ...saved });
  }, []);

  const set = <K extends keyof StudentProfile>(k: K, v: StudentProfile[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const canSubmit =
    form.name.trim().length > 0 && (form.skills.length > 0 || form.interests.length > 0);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await api.saveStudent(form);
      profileStore.set(saved);
      router.push("/recommendations?fresh=1");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong saving your profile.");
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <p className="text-sm text-deep-teal">Onboarding</p>
      <h1 className="mt-1 font-display text-3xl">Chart your profile</h1>
      <p className="mt-3 text-charcoal-text/75">
        This is the point we plot on the map. The more concrete the skills and interests, the sharper
        the bearing &mdash; vague inputs get a vague reading, and we&rsquo;ll tell you so.
      </p>

      <form onSubmit={submit} className="mt-8 space-y-7">
        <div>
          <label htmlFor="name" className="mb-1 block text-sm font-medium">
            Name
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

        <TagInput
          label="Skills"
          hint="Tools, languages, techniques you can already use. Press Enter or comma to add."
          values={form.skills}
          onChange={(v) => set("skills", v)}
          placeholder="Python, linear algebra, React..."
          suggestions={SKILL_SUGGESTIONS}
        />

        <TagInput
          label="Interests"
          hint="Problem areas and topics you want the project to be about."
          values={form.interests}
          onChange={(v) => set("interests", v)}
          placeholder="quantum machine learning, optimization..."
          suggestions={INTEREST_SUGGESTIONS}
        />

        <fieldset>
          <legend className="mb-2 text-sm font-medium">Technical comfort</legend>
          <div className="grid gap-2 sm:grid-cols-3">
            {COMFORT.map((c) => (
              <label
                key={c.value}
                className={`chart-card cursor-pointer p-3 text-sm transition-colors ${
                  form.tech_comfort === c.value
                    ? "border-deep-teal ring-1 ring-deep-teal"
                    : "hover:border-deep-teal/50"
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
                <span className="block text-xs text-charcoal-text/60">{c.hint}</span>
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
            rows={3}
            value={form.prior_projects}
            onChange={(e) => set("prior_projects", e.target.value)}
            className="chart-card w-full bg-parchment-raised px-3 py-2 text-sm outline-none"
            placeholder="A sentence or two about what you've built before - this feeds the match too."
          />
        </div>

        <div>
          <label htmlFor="outcome" className="mb-1 block text-sm font-medium">
            Preferred outcome type
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
          <p role="alert" className="chart-card border-l-2 border-l-brass p-3 text-sm">
            {error}
          </p>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button type="submit" className="btn btn-primary" disabled={!canSubmit || busy}>
            {busy ? "Plotting..." : "Take a bearing"}
          </button>
          {!canSubmit && (
            <span className="text-xs text-charcoal-text/60">
              Add your name and at least one skill or interest.
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
