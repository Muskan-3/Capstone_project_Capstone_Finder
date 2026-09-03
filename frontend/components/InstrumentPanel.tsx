"use client";

import Link from "next/link";
import { fmt } from "@/lib/format";
import type { RecommendationResponse, StudentProfile } from "@/lib/types";

export function InstrumentPanel({
  profile,
  result,
  minBand,
  onMinBand,
  hiddenCount,
}: {
  profile: StudentProfile;
  result: RecommendationResponse | null;
  minBand: "weak" | "moderate" | "strong";
  onMinBand: (b: "weak" | "moderate" | "strong") => void;
  hiddenCount: number;
}) {
  const dist = result?.cluster_distribution.slice(0, 5) ?? [];
  const routed = new Set(result?.routed_clusters ?? []);

  return (
    <aside className="lg:sticky lg:top-[64px] lg:h-fit">
      <div className="panel p-4">
        <p className="readout-label">Instrument panel</p>
        <h2 className="mt-0.5 font-display text-lg">{profile.name || "Your profile"}</h2>

        <div className="mt-2">
          <div className="readout-row">
            <span className="readout-label">Technical comfort</span>
            <span className="data-token text-sm">{profile.tech_comfort}</span>
          </div>
          <div className="readout-row">
            <span className="readout-label">Skills plotted</span>
            <span className="data-token text-sm">{profile.skills.length}</span>
          </div>
          <div className="readout-row">
            <span className="readout-label">Interests plotted</span>
            <span className="data-token text-sm">{profile.interests.length}</span>
          </div>
          {result && (
            <>
              <div className="readout-row">
                <span className="readout-label">Routing confidence</span>
                <span className="data-token text-sm">{fmt(result.cluster_confidence)}</span>
              </div>
              <div className="readout-row">
                <span className="readout-label">Model version</span>
                <span className="data-token text-sm">
                  {result.model_version != null ? `v${result.model_version}` : "-"}
                </span>
              </div>
            </>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {[...profile.skills, ...profile.interests].slice(0, 10).map((t) => (
            <span key={t} className="pill">
              {t}
            </span>
          ))}
        </div>
        <Link href="/onboarding" className="link-teal mt-3 inline-block text-xs">
          Edit profile
        </Link>
      </div>

      {dist.length > 0 && (
        <div className="panel mt-4 p-4">
          <p className="readout-label">Bearing to each domain cluster</p>
          <ul className="mt-2 space-y-2">
            {dist.map((c) => {
              const w = Math.max(3, Math.min(100, (c.similarity / (dist[0].similarity || 1)) * 100));
              const on = routed.has(c.cluster_id);
              return (
                <li key={c.cluster_id}>
                  <div className="flex items-baseline justify-between gap-2 text-xs">
                    <span className={on ? "font-medium text-deep-teal" : "text-charcoal-text/70"}>
                      {c.label}
                    </span>
                    <span className="data-token text-charcoal-text/55">
                      {fmt(c.similarity)} &middot; n={c.size}
                    </span>
                  </div>
                  <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-hairline">
                    <span
                      className="block h-full"
                      style={{
                        width: `${w}%`,
                        background: on ? "var(--deep-teal)" : "var(--brass-soft)",
                      }}
                    />
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="panel mt-4 p-4">
        <p className="readout-label">Filters</p>
        <p className="mt-1 text-xs text-charcoal-text/60">Minimum signal to show</p>
        <div className="mt-2 grid grid-cols-3 gap-1">
          {(["weak", "moderate", "strong"] as const).map((b) => (
            <button
              key={b}
              type="button"
              onClick={() => onMinBand(b)}
              aria-pressed={minBand === b}
              className={`rounded-sm border px-2 py-1 text-xs capitalize transition-colors ${
                minBand === b
                  ? "border-deep-teal bg-deep-teal/10 text-deep-teal"
                  : "border-hairline text-charcoal-text/70 hover:border-deep-teal/50"
              }`}
            >
              {b}
            </button>
          ))}
        </div>
        {hiddenCount > 0 && (
          <p className="mt-2 text-xs text-charcoal-text/55">
            {hiddenCount} result{hiddenCount > 1 ? "s" : ""} hidden below this threshold.
          </p>
        )}
      </div>

      <div className="panel mt-4 p-4">
        <p className="readout-label">Faculty matching</p>
        <p className="mt-1 text-xs text-charcoal-text/70">
          Not yet active &mdash; no supervisor preference data has been collected. This signal is
          weighted at 0 in the score.
        </p>
      </div>
    </aside>
  );
}
