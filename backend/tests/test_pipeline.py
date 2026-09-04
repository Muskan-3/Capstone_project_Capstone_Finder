"""Section 5 / Definition-of-Done: routing + honest degradation."""

from __future__ import annotations

import pytest

from app.config import settings
from app.ml.ingest import clean, read_source
from app.ml.pipeline import DocMeta, train
from app.ml.recommender import StudentProfile, correct_typos, parse_refinement, recommend, refine

_KW = dict(
    route_threshold=settings.route_confidence_threshold,
    serendipity=settings.serendipity_cross_cluster,
    weights={"relevance": 0.8, "feasibility": 0.2, "faculty": 0.0},
    mmr_lambda=settings.mmr_lambda,
    top_k=5,
    band_strong=settings.band_strong,
    band_moderate=settings.band_moderate,
)


@pytest.fixture(scope="module")
def art():
    sheet, raw = read_source(settings.source_workbook)
    rows, _ = clean(raw, source="t", sheet=sheet, source_batch="initial")
    docs = [
        DocMeta(i, r.project_id, r.title or "", r.statement or "", "initial")
        for i, r in enumerate(rows)
        if not r.is_flagged and (r.title or r.statement)
    ]
    return train(docs, version=0, k_min=settings.kmeans_k_min, k_max=settings.kmeans_k_max)


def test_cluster_sweep_in_range(art):
    assert settings.kmeans_k_min <= art.k <= settings.kmeans_k_max
    assert set(art.silhouette_by_k) <= set(range(settings.kmeans_k_min, settings.kmeans_k_max + 1))


def test_quantum_profile_is_routed(art):
    p = StudentProfile(
        skills=["qiskit", "python", "linear algebra"],
        interests=["quantum machine learning", "variational circuits"],
    )
    res = recommend(art, p, **_KW)
    assert res.mode == "routed"
    assert len(res.recommendations) == 5
    assert all(r.similarity < 1.0 for r in res.recommendations)  # never a "perfect" match


def test_non_quantum_profile_not_force_matched(art):
    p = StudentProfile(
        skills=["react", "typescript", "css", "node"],
        interests=["web design", "accessibility", "developer tooling"],
    )
    res = recommend(art, p, **_KW)
    assert res.mode in {"low_confidence", "no_signal"}
    assert res.cluster_confidence < settings.route_confidence_threshold
    # if anything is shown it must carry a real, low score - not dressed up as strong
    assert all(r.confidence_band in {"weak", "moderate"} for r in res.recommendations)


def test_every_recommendation_cites_a_real_project_id(art):
    p = StudentProfile(skills=["cryptography", "python"], interests=["post-quantum", "key distribution"])
    res = recommend(art, p, **_KW)
    known = {d.project_id for d in art.docs_meta}
    assert all(r.project_id in known for r in res.recommendations)
    assert all(isinstance(r.explanation["cosine_similarity"], float) for r in res.recommendations)


def test_mmr_returns_distinct_items(art):
    p = StudentProfile(skills=["python", "machine learning"], interests=["optimization", "quantum"])
    res = recommend(art, p, **_KW)
    pids = [r.project_id for r in res.recommendations]
    assert len(pids) == len(set(pids))


def test_refinement_parsing():
    parse = parse_refinement("show me more optimization ideas, avoid AR/VR and simulation")
    assert "ar/vr" in parse.negative
    assert "simulation" in parse.negative  # polarity carried across "and"
    assert any("optimization" in p for p in parse.positive)


def test_typo_correction_fixes_domain_words_without_mangling_real_words(art):
    vocab = art.unigram_vocab()
    # a genuine domain typo should resolve to the real corpus term
    assert correct_typos("quatum", vocab) == "quantum"
    # a legitimate English word that just isn't domain vocabulary must survive
    # untouched - regression test for a real bug where "field" (not in this
    # narrow corpus) got fuzzy-matched into an unrelated in-vocabulary word
    # ("yield", from crop-yield statements) purely by edit distance.
    assert correct_typos("field", vocab) == "field"


def test_chat_refine_does_not_leak_cross_domain_results(art):
    """A student who explicitly names one domain in chat should not have
    unrelated-cluster statements padded into the results "for breadth" -
    regression test for a real complaint: asking for "the medical field"
    surfaced logistics/supply-chain statements alongside genuine matches."""
    p = StudentProfile(skills=["python"], interests=[])
    res, parse = refine(
        art, p, "i want to work in the medical field quatum suggeste me in that field", **_KW
    )
    assert "quantum" in parse.positive  # the typo was corrected
    if res.mode == "routed":
        # every result must come from a cluster the routing actually chose -
        # none smuggled in from an unrelated domain "for breadth"
        assert all(r.cluster_id in res.routed_clusters for r in res.recommendations)
