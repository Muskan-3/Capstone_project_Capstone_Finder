"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Recommendation } from "@/lib/types";

/** Scores stay internal: the card shows what matched and why, never a number. */
export function RecommendationCard({
  rec,
  primary = false,
}: {
  rec: Recommendation;
  primary?: boolean;
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
      <div className="min-w-0">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="data-token text-xs text-charcoal-text/55">#{rec.rank}</span>
          {rec.domain && <span className="pill">{rec.domain}</span>}
          <span className="data-token pill" title="Real Project ID - look it up in the catalogue">
            {rec.project_id}
          </span>
          {rec.source && (
            <span
              className="rounded-full border border-hairline px-2 py-0.5 text-[10px] uppercase tracking-wide text-charcoal-text/55"
              title="Where this problem statement came from"
            >
              {rec.source}
            </span>
          )}
        </div>
        <h3 id={`rec-${rec.rank}-title`} className="font-display text-xl leading-snug">
          {rec.title}
        </h3>
        <p className="mt-2 text-sm text-charcoal-text/80">{rec.adapted_text}</p>
        {rec.diversity_note && (
          <p className="mt-3 text-xs text-charcoal-text/55">{rec.diversity_note}</p>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-3">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="link-teal text-sm"
        >
          {open ? "Hide explanation" : "Explain this match"}
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
          <div>
            <p className="readout-label mb-1.5">Why this domain</p>
            <p className="text-xs text-charcoal-text/70">{routingReason(ex.routing)}</p>
          </div>
          <div>
            <p className="readout-label mb-1.5">Which of your terms drove this</p>
            {ex.top_term_drivers.length === 0 ? (
              <p className="text-xs text-charcoal-text/60">
                No direct word overlap &mdash; this one was kept for variety within the domain.
              </p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {ex.top_term_drivers.map((d) => (
                  <li key={d.term} className="pill">
                    {d.term}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </article>
  );
}

function routingReason(routing: Recommendation["explanation"]["routing"]): string {
  const domains = routing.domains.join(" and ") || "the whole catalogue";
  const words = Object.values(routing.keyword_hits ?? {}).flat();
  if (routing.source === "keyword" && words.length) {
    return `You mentioned ${words.map((w) => `“${w}”`).join(", ")}, so results come from ${domains}.`;
  }
  if (routing.source === "classifier") {
    return `Your wording is closest to statements in ${domains}, so results come from there.`;
  }
  return `Results come from ${domains}.`;
}
