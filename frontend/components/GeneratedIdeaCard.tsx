"use client";

import { fmt } from "@/lib/format";
import type { GeneratedIdea } from "@/lib/types";

/** Generate-mode card. Visibly distinct from RecommendationCard and never shows
 *  a Project ID: these ideas are not catalogue rows. */
export function GeneratedIdeaCard({ idea, index }: { idea: GeneratedIdea; index: number }) {
  return (
    <article
      className="chart-card border border-dashed border-deep-teal/40 p-5 sm:p-6"
      aria-labelledby={`idea-${index}-title`}
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="data-token text-xs text-charcoal-text/55">idea {index}</span>
        <span className="pill">{idea.domain}</span>
        <span className="pill">{idea.level}</span>
      </div>
      <p className="mb-2 text-xs font-medium text-deep-teal">{idea.label}</p>
      <h3 id={`idea-${index}-title`} className="font-display text-xl leading-snug">
        {idea.title}
      </h3>
      <p className="mt-2 text-sm text-charcoal-text/80">{idea.description}</p>
      <p className="mt-3 border-t border-hairline pt-3 text-xs text-charcoal-text/60">
        Novelty{" "}
        <span className="data-token">{idea.novelty == null ? "-" : fmt(idea.novelty, 2)}</span>{" "}
        &mdash; 1 minus its closest cosine similarity to any statement in the catalogue.
      </p>
    </article>
  );
}
