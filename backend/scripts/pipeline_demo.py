"""Section 11, step 2 - exercise the pipeline standalone with sample profiles.

Confirms the core claim of the design: a non-quantum profile is NOT flooded with
quantum results - it either gets genuine non-quantum matches or the honest
low-confidence state.

    python -m scripts.pipeline_demo
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.ml.ingest import clean, read_source  # noqa: E402
from app.ml.pipeline import DocMeta, train  # noqa: E402
from app.ml.recommender import StudentProfile, recommend, refine  # noqa: E402

PROFILES = {
    "quantum-leaning": StudentProfile(
        skills=["python", "qiskit", "linear algebra", "pennylane"],
        interests=["quantum machine learning", "variational circuits", "optimization"],
        prior_projects="Built a variational quantum classifier for MNIST digits.",
        preferred_outcome="research prototype",
    ),
    "quantum-adjacent (security)": StudentProfile(
        skills=["cryptography", "python", "networking"],
        interests=["post-quantum cryptography", "key distribution", "secure communication"],
        prior_projects="Implemented RSA and studied lattice-based schemes.",
    ),
    "non-quantum (web dev)": StudentProfile(
        skills=["react", "typescript", "node.js", "postgresql", "rest apis"],
        interests=["web applications", "developer tools", "accessibility", "ui design"],
        prior_projects="Shipped a full-stack marketplace with Next.js and Stripe.",
        preferred_outcome="deployable web app",
    ),
    "non-quantum (industrial design)": StudentProfile(
        skills=["cad", "titanium machining", "product design", "prototyping"],
        interests=["hardware finishing", "consumer devices", "materials"],
        prior_projects="Designed a CNC-machined watch case.",
    ),
}


def _fmt(result) -> None:
    print(f"    mode: {result.mode}   routing confidence: {result.cluster_confidence}")
    print(f"    {result.message}")
    top = result.cluster_distribution[:3]
    print("    cluster distribution (top 3): "
          + ", ".join(f"[{c['label']}] sim={c['similarity']} n={c['size']}" for c in top))
    for rec in result.recommendations:
        print(f"      #{rec.rank}  cos={rec.similarity:<6}  {rec.confidence_band:<8}  "
              f"[{rec.cluster_label}]  {rec.project_id}  {rec.title[:54]}")
    if not result.recommendations:
        print("      (no items returned - honest empty state)")


def main() -> int:
    sheet, raw = read_source(settings.source_workbook)
    rows, _ = clean(raw, source="demo", sheet=sheet, source_batch="initial")
    docs = [
        DocMeta(i, r.project_id, r.title or "", r.statement or "", "initial")
        for i, r in enumerate(rows)
        if not r.is_flagged and (r.title or r.statement)
    ]
    art = train(docs, version=0, k_min=settings.kmeans_k_min, k_max=settings.kmeans_k_max)

    print(f"trained: k={art.k}  silhouette={art.silhouette:.4f}  corpus={art.corpus_size}")
    print("silhouette by k:", {k: round(v, 4) for k, v in art.silhouette_by_k.items()})
    print("\nclusters:")
    for cid in sorted(art.cluster_sizes):
        print(f"  {cid}: n={art.cluster_sizes[cid]:<3}  {art.cluster_label(cid)}  "
              f"| {', '.join(art.cluster_terms[cid][:6])}")

    kw = dict(
        route_threshold=settings.route_confidence_threshold,
        serendipity=settings.serendipity_cross_cluster,
        weights={
            "relevance": settings.weight_relevance,
            "feasibility": settings.weight_feasibility,
            "faculty": settings.weight_faculty,
        },
        mmr_lambda=settings.mmr_lambda,
        top_k=settings.top_k,
        band_strong=settings.band_strong,
        band_moderate=settings.band_moderate,
    )

    for name, profile in PROFILES.items():
        print("\n" + "=" * 92)
        print(f"PROFILE: {name}")
        print("=" * 92)
        _fmt(recommend(art, profile, **kw))

    print("\n" + "=" * 92)
    print("REFINEMENT: quantum-leaning + 'show me more optimization ideas, avoid AR/VR'")
    print("=" * 92)
    res, parse = refine(art, PROFILES["quantum-leaning"],
                        "show me more optimization ideas, avoid AR/VR", **kw)
    print(f"  parsed -> positive={parse.negative and parse.positive or parse.positive}, "
          f"negative={parse.negative}")
    _fmt(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
