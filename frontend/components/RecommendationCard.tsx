"use client";

import { useState } from "react";
import { MatchCompass } from "./MatchCompass";
import { api } from "@/lib/api";
import { fmt, pct } from "@/lib/format";
import type { Recommendation } from "@/lib/types";

export function RecommendationCard({
  rec,
  primary = false,
  settle = true,
}: {
  rec: Recommendation;
  primary?: boolean;
  settle?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [verdict, setVerdict] = useState<"accept" | "reject" | null>(null);
  const ex = rec.explanation;

  const sendFeedback = async (v: "accept" | "reject") => {
    setVerdict(v);
    if (rec.recommendation_id) {
      try {
        await api.feedback(rec.recommendation_id, v);
      } catch {
        /* feedback is best-effort; the UI has already acknowledged */
      }
    }
  };

  return (
    <article
      className={`chart-card ${primary ? "chart-card--primary" : ""} p-5 sm:p-6`}
      aria-labelledby={`rec-${rec.rank}-title`}
    >
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="data-token text-xs text-charcoal-text/55">#{rec.rank}</span>
            <span className="pill">{rec.cluster_label}</span>
            <span className="data-token pill" title="Real Project ID - look it up in the catalogue">
              {rec.project_id}
            </span>
          </div>
          <h3 id={`rec-${rec.rank}-title`} className="font-display text-xl leading-snug">
            {rec.title}
          </h3>
          <p className="mt-2 text-sm text-charcoal-text/80">{rec.adapted_text}</p>
          {rec.diversity_note && (
            <p className="mt-3 text-xs text-charcoal-text/55">{rec.diversity_note}</p>
          )}
        </div>

        <div className="shrink-0 self-center sm:self-start">
          <MatchCompass similarity={rec.similarity} band={rec.confidence_band} settle={settle} />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-3">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="link-teal text-sm"
        >
          {open ? "Hide the maths" : "Explain this match"}
        </button>

        <div className="flex items-center gap-2 text-sm">
          {verdict ? (
            <span className="text-xs text-charcoal-text/60">
              Noted &mdash; you {verdict === "accept" ? "kept" : "dismissed"} this. Thanks.
            </span>
          ) : (
            <>
              <span className="text-xs text-charcoal-text/55">Useful?</span>
              <button type="button" onClick={() => sendFeedback("accept")} className="btn btn-ghost !py-1 !px-2.5 text-xs">
                Keep
              </button>
              <button type="button" onClick={() => sendFeedback("reject")} className="btn btn-ghost !py-1 !px-2.5 text-xs">
                Not for me
              </button>
            </>
          )}
        </div>
      </div>

      {open && (
        <div className="mt-4 space-y-3 rounded-panel bg-parchment p-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="cosine similarity" value={fmt(ex.cosine_similarity)} note="student vector vs. statement vector" />
            <Metric label="feasibility proxy" value={fmt(ex.feasibility, 2)} note={ex.feasibility_basis} />
            <Metric label="composite score" value={fmt(ex.composite_score)} note="used for ranking" />
          </div>

          <div>
            <p className="readout-label mb-1.5">Which of your terms drove this</p>
            {ex.top_term_drivers.length === 0 ? (
              <p className="text-xs text-charcoal-text/60">
                No direct vocabulary overlap &mdash; this came in on the cross-cluster sample.
              </p>
            ) : (
              <ul className="space-y-1.5">
                {ex.top_term_drivers.map((d) => (
                  <li key={d.term} className="flex items-center gap-2">
                    <span className="data-token w-40 shrink-0 truncate text-xs">{d.term}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-hairline">
                      <span
                        className="block h-full bg-deep-teal"
                        style={{ width: pct(d.share, 0) }}
                      />
                    </span>
                    <span className="data-token w-10 shrink-0 text-right text-xs text-charcoal-text/60">
                      {pct(d.share, 0)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <p className="text-xs text-charcoal-text/60">
            composite ={" "}
            {Object.entries(ex.weights)
              .map(([k, v]) => `${v.toFixed(2)}·${k}`)
              .join(" + ")}
            . Routing mode <span className="data-token">{ex.routing.mode}</span> at confidence{" "}
            <span className="data-token">{fmt(ex.routing.cluster_confidence)}</span> (threshold{" "}
            <span className="data-token">{fmt(ex.routing.threshold, 2)}</span>).
          </p>
        </div>
      )}
    </article>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-panel border border-hairline bg-parchment-raised p-3">
      <p className="readout-label">{label}</p>
      <p className="data-token mt-0.5 text-lg">{value}</p>
      <p className="mt-1 text-[11px] leading-tight text-charcoal-text/55">{note}</p>
    </div>
  );
}
