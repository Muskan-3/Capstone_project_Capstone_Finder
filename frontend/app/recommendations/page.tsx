"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { InstrumentPanel } from "@/components/InstrumentPanel";
import { LoadingCompass } from "@/components/LoadingCompass";
import { RecommendationCard } from "@/components/RecommendationCard";
import { RefineBar } from "@/components/RefineBar";
import { api, ApiError } from "@/lib/api";
import { profileStore, resultStore } from "@/lib/store";
import type { RecommendationResponse, StudentProfile } from "@/lib/types";

const BAND_RANK = { weak: 0, moderate: 1, strong: 2 } as const;

export default function RecommendationsPage() {
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refining, setRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [minBand, setMinBand] = useState<"weak" | "moderate" | "strong">("weak");
  const [settleKey, setSettleKey] = useState(0);
  const bootstrapped = useRef(false);

  const generate = useCallback(async (p: StudentProfile) => {
    if (p.id == null) {
      setError("Your saved profile is missing an id. Please re-submit the onboarding form.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.recommend(p.id);
      setResult(res);
      resultStore.set(res);
      setSettleKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate recommendations.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    const p = profileStore.get();
    if (!p) {
      setLoading(false);
      return;
    }
    setProfile(p);
    const fresh = new URLSearchParams(window.location.search).get("fresh");
    const cached = resultStore.get();
    if (cached && !fresh) {
      setResult(cached);
      setLoading(false);
      setSettleKey((k) => k + 1);
    } else {
      void generate(p);
    }
  }, [generate]);

  const refine = async (constraint: string) => {
    if (!profile?.id) return;
    setRefining(true);
    setError(null);
    try {
      const res = await api.refine(profile.id, constraint);
      setResult(res);
      resultStore.set(res);
      setSettleKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Refinement failed.");
    } finally {
      setRefining(false);
    }
  };

  const visible = useMemo(() => {
    if (!result) return [];
    return result.recommendations.filter(
      (r) => BAND_RANK[r.confidence_band] >= BAND_RANK[minBand],
    );
  }, [result, minBand]);

  const hiddenCount = (result?.recommendations.length ?? 0) - visible.length;

  if (!loading && !profile) {
    return (
      <div className="mx-auto max-w-xl px-4 py-20 text-center sm:px-6">
        <h1 className="font-display text-2xl">No profile plotted yet</h1>
        <p className="mt-3 text-charcoal-text/75">
          The workspace needs a profile to take a bearing from.
        </p>
        <Link href="/onboarding" className="btn btn-primary mt-6">
          Chart my profile
        </Link>
      </div>
    );
  }

  const modeTone =
    result?.mode === "routed"
      ? "border-l-deep-teal"
      : result?.mode === "low_confidence"
        ? "border-l-brass"
        : "border-l-charcoal-text/40";

  return (
    <div className="flex min-h-screen flex-col">
      <div className="mx-auto w-full max-w-chart flex-1 px-4 py-8 pb-40 sm:px-6">
        <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
          {profile && (
            <InstrumentPanel
              profile={profile}
              result={result}
              minBand={minBand}
              onMinBand={setMinBand}
              hiddenCount={hiddenCount}
            />
          )}

          <section aria-live="polite">
            <div className="mb-4 flex items-end justify-between gap-4">
              <div>
                <p className="text-sm text-deep-teal">Recommendations workspace</p>
                <h1 className="font-display text-2xl">Nearest routes</h1>
              </div>
              {profile && (
                <button
                  type="button"
                  onClick={() => generate(profile)}
                  className="btn btn-ghost !py-1.5 text-xs"
                  disabled={loading}
                >
                  Regenerate
                </button>
              )}
            </div>

            {error && (
              <p role="alert" className="chart-card border-l-2 border-l-brass p-4 text-sm">
                {error}
              </p>
            )}

            {loading ? (
              <LoadingCompass />
            ) : result ? (
              <>
                <div className={`chart-card border-l-2 ${modeTone} mb-5 p-4`}>
                  <p className="text-sm font-medium capitalize">
                    {result.mode.replace("_", " ")}
                  </p>
                  <p className="mt-1 text-sm text-charcoal-text/80">{result.message}</p>
                  {result.refinement && (
                    <p className="mt-2 text-xs text-charcoal-text/60">
                      excluded: {result.refinement.negative.join(", ") || "none"} &nbsp;·&nbsp;
                      boosted: {result.refinement.positive.join(", ") || "none"}
                    </p>
                  )}
                </div>

                {result.mode === "no_signal" || result.recommendations.length === 0 ? (
                  <div className="chart-card p-6 text-sm text-charcoal-text/75">
                    Nothing to chart from this profile yet.{" "}
                    <Link href="/onboarding" className="link-teal">
                      Add more concrete skills or interests
                    </Link>{" "}
                    and try again.
                  </div>
                ) : (
                  <div className="space-y-5">
                    {visible.map((rec) => (
                      <RecommendationCard
                        key={`${settleKey}-${rec.project_id}`}
                        rec={rec}
                        primary={rec.rank === 1 && result.mode === "routed"}
                        settle
                      />
                    ))}
                    {visible.length === 0 && (
                      <div className="chart-card p-6 text-sm text-charcoal-text/70">
                        All {result.recommendations.length} results are below the{" "}
                        <span className="font-medium capitalize">{minBand}</span> threshold. Lower
                        the minimum signal in the instrument panel to see them with their real
                        scores.
                      </div>
                    )}
                  </div>
                )}

                <p className="mt-6 text-xs text-charcoal-text/50">
                  {result.scoring_formula}
                </p>
              </>
            ) : null}
          </section>
        </div>
      </div>

      <RefineBar onRefine={refine} busy={refining} disabled={loading || !result} />
    </div>
  );
}
