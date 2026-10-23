"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CompassMark } from "@/components/CompassMark";
import { api } from "@/lib/api";
import { fmt, shortDate } from "@/lib/format";
import type { ModelStatus } from "@/lib/types";

export default function AboutPage() {
  const [status, setStatus] = useState<ModelStatus | null>(null);

  useEffect(() => {
    api.modelStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <p className="flex items-center gap-2 text-sm text-deep-teal">
        <CompassMark size={18} /> How it works
      </p>
      <h1 className="mt-1 font-display text-3xl">A compass, not an oracle</h1>

      <p className="mt-4 text-charcoal-text/80">
        Capstone Compass does not use a large language model, and it does not call the internet. It
        is built entirely on classical information retrieval running against the department&rsquo;s
        own catalogue of capstone problem statements.
      </p>

      {status && (
        <div className="panel mt-6 grid grid-cols-2 gap-px overflow-hidden bg-hairline sm:grid-cols-4">
          <Fact label="Statements in catalogue" value={String(status.corpus_size)} />
          <Fact label="In the active pool" value={String(status.active_corpus_size)} />
          <Fact label="Domain clusters" value={String(status.cluster_count ?? "-")} />
          <Fact
            label="Model last trained"
            value={status.last_trained_at ? shortDate(status.last_trained_at) : "-"}
            small
          />
        </div>
      )}

      <Section title="1 · Turning text into coordinates (TF-IDF)">
        Every problem statement, and your profile, is converted into a vector by a{" "}
        <span className="data-token">TfidfVectorizer</span> &mdash; term frequency &times; inverse
        document frequency over 1- and 2-word phrases, capped at 5,000 features. Words that are
        common everywhere (&ldquo;system&rdquo;, &ldquo;data&rdquo;) count for little; words that
        distinguish one statement from another (&ldquo;variational&rdquo;, &ldquo;QKD&rdquo;,
        &ldquo;segmentation&rdquo;) count for a lot. The vocabulary is learned from this corpus
        alone; nothing is downloaded.
      </Section>

      <Section title="2 · Grouping the map into regions (KMeans)">
        The vectors are clustered with KMeans. We sweep k from{" "}
        {status?.silhouette_by_k && Object.keys(status.silhouette_by_k).length
          ? Object.keys(status.silhouette_by_k)[0]
          : "4"}{" "}
        to{" "}
        {status?.silhouette_by_k && Object.keys(status.silhouette_by_k).length
          ? Object.keys(status.silhouette_by_k).slice(-1)[0]
          : "10"}{" "}
        and keep the k with the best cosine silhouette score. These clusters are a descriptive
        topic map for the admin views only - they no longer decide where a request is routed.
        {status?.clusters && status.clusters.length > 0 && (
          <ul className="mt-3 grid gap-1.5 sm:grid-cols-2">
            {status.clusters.map((c) => (
              <li key={c.cluster_id} className="text-sm">
                <span className="text-deep-teal">{c.label}</span>{" "}
                <span className="data-token text-xs text-charcoal-text/55">n={c.size}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="3 · Picking a domain, then ranking">
        Every statement carries a domain. Your request is routed by a keyword map first
        (&ldquo;react&rdquo; &rarr; Web/Mobile, &ldquo;arduino&rdquo; &rarr; IoT); if no keyword
        fires, a TF-IDF + logistic-regression classifier trained on the catalogue picks the domain.
        Before anything is shown, the closest statements inside that domain must be genuinely close
        to your words &mdash; and for a classifier guess, your nearest statements must cluster in one
        domain rather than scatter. If not, you get no projects, just domains to try. Otherwise we
        rank inside the domain, blend in a simple length-based feasibility proxy, and spread the top
        five with Maximal Marginal Relevance so they aren&rsquo;t five versions of one idea.
      </Section>

      <Section title="4 · What you see is retrieved, not written">
        The text on each recommendation is the real problem statement from the catalogue, wrapped in
        a fixed sentence that names the skill and interest of yours that matched. Nothing is
        generated. Every card shows a real Project ID you can look up, its domain, and the words of
        yours that matched it.
      </Section>

      <h2 className="mt-10 font-display text-2xl">Standing disclosures</h2>
      <ul className="mt-3 space-y-2 text-sm text-charcoal-text/80">
        <Disclosure>
          Every recommendation cites a real <span className="data-token">project_id</span>. Match
          scores are used internally for ranking and are not shown as a rating; there is no
          &ldquo;perfect&rdquo; or &ldquo;guaranteed&rdquo; match.
        </Disclosure>
        <Disclosure>
          When there isn&rsquo;t enough evidence for a request, the workspace shows no projects and
          suggests domains to try instead.
        </Disclosure>
        <Disclosure>
          Recommendations are retrieval + adaptation over{" "}
          {status ? `${status.corpus_size} statements` : "the local corpus"}, not generative AI.
        </Disclosure>
        <Disclosure>
          Faculty matching exists in the database and admin UI but is weighted at 0 in scoring until
          real supervisor preference data is entered &mdash; the source workbook only contains a
          review-assignment tracker.
        </Disclosure>
        <Disclosure>
          The catalogue is expected to grow by 300&ndash;400 more statements across broader domains;
          ingestion and retraining are a repeatable pipeline in the admin panel.
        </Disclosure>
      </ul>

      <div className="mt-10">
        <Link href="/login" className="btn btn-primary">
          Log in &amp; chat
        </Link>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="font-display text-xl">{title}</h2>
      <div className="mt-2 text-sm text-charcoal-text/80">{children}</div>
    </section>
  );
}

function Fact({ label, value, small }: { label: string; value: string; small?: boolean }) {
  return (
    <div className="bg-parchment-raised p-4">
      <p className="readout-label">{label}</p>
      <p className={`data-token mt-1 ${small ? "text-sm" : "text-2xl"}`}>{value}</p>
    </div>
  );
}

function Disclosure({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex gap-2">
      <span aria-hidden className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brass" />
      <span>{children}</span>
    </li>
  );
}
