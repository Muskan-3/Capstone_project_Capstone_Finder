"""Route -> rank -> diversify -> explain -> adapt text.

Steps 4-7 of Section 5. Pure functions over a ``ModelArtifacts`` snapshot and a
student profile dict. No database access, no text generation - the shown text is
the real corpus statement wrapped in a fixed rationale template, and every item
carries its real ``project_id`` and its real cosine score.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize
from spellchecker import SpellChecker

from .pipeline import DocMeta, ModelArtifacts

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+.#-]{1,}")

# A bundled, offline word-frequency dictionary (no network call, ships with the
# package) - used only to decide whether a word is *already* legitimate
# English before ever attempting to "correct" it. Loaded once at import.
_ENGLISH = SpellChecker(distance=1)


def correct_typos(text: str, vocabulary: set[str] | None) -> str:
    """Fix typed-in typos before they silently vanish as out-of-vocabulary
    noise in the TF-IDF match (e.g. "quatum" -> "quantum").

    Two-layer, both fully offline / grounded, never a hosted model:
      1. If a word is already valid English (bundled dictionary), leave it
         alone - this is what stops a real word like "field" (just not one
         that happens to appear in this narrow corpus) from being mangled
         into an unrelated in-vocabulary word like "yield".
      2. Otherwise fuzzy-match it against words that actually appear in the
         *trained corpus vocabulary* - so a correction is only ever made
         into a term this catalogue can actually match on, never an external
         dictionary word chosen at random.
    """
    if not text:
        return text

    def fix(m: re.Match[str]) -> str:
        word = m.group(0)
        lower = word.lower()
        if len(lower) < 5 or lower in _ENGLISH or (vocabulary and lower in vocabulary):
            return word
        if vocabulary:
            match = difflib.get_close_matches(lower, vocabulary, n=1, cutoff=0.8)
            if match:
                return match[0]
        corrected = _ENGLISH.correction(lower)
        return corrected if corrected else word

    return _WORD.sub(fix, text)

# cosine similarity that maps to a "full" relevance bar. No student/statement pair
# in the seed corpus exceeds ~0.42, so the relevance term never actually saturates -
# there is deliberately no path to a displayed "100% / perfect match".
REL_SCALE = 0.50


@dataclass
class StudentProfile:
    skills: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    prior_projects: str = ""
    tech_comfort: str = "moderate"
    preferred_outcome: str = ""

    def query_text(self) -> str:
        parts = list(self.skills) + list(self.interests)
        if self.prior_projects:
            parts.append(self.prior_projects)
        if self.preferred_outcome:
            parts.append(self.preferred_outcome)
        return " ".join(parts).strip()


@dataclass
class Rec:
    rank: int
    project_id: str
    title: str
    statement: str
    adapted_text: str
    cluster_id: int
    cluster_label: str
    similarity: float          # raw cosine, student vs statement (0..1)
    composite_score: float     # weighted blend actually used for ranking
    feasibility: float
    confidence_band: str       # strong | moderate | weak
    diversity_note: str
    explanation: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecResult:
    mode: str                  # "routed" | "low_confidence" | "no_signal"
    message: str
    routed_cluster: int | None
    cluster_confidence: float
    cluster_distribution: list[dict[str, Any]]
    scoring_formula: str
    weights: dict[str, float]
    recommendations: list[Rec]
    routed_clusters: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommendations"] = [r.as_dict() for r in self.recommendations]
        return d


# --------------------------------------------------------------------------- #
# feasibility heuristic  (documented, deliberately simple - shown in the UI)
# --------------------------------------------------------------------------- #
def feasibility_score(statement: str) -> float:
    """A length-based proxy for how well-scoped a statement is for a capstone.

    Very short statements are under-specified; very long ones tend to be
    over-scoped. The sweet spot is a focused paragraph. This is a heuristic,
    not a judgement of the idea - it is surfaced verbatim in "Explain this match".
    """
    n = len(statement or "")
    if n < 120:
        return 0.70
    if n < 250:
        return 0.85
    if n <= 900:
        return 1.00
    if n <= 1400:
        return 0.92
    return 0.80


FEASIBILITY_DOC = (
    "feasibility = length-based scoping proxy: <120 chars -> 0.70, <250 -> 0.85, "
    "250-900 -> 1.00, 900-1400 -> 0.92, >1400 -> 0.80"
)


def _confidence_band(sim: float, strong: float, moderate: float) -> str:
    if sim >= strong:
        return "strong"
    if sim >= moderate:
        return "moderate"
    return "weak"


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _WORD.finditer(text or "")]


def _pick_phrase(candidates: list[str], doc_text: str, fallback: str) -> str:
    """Choose the student phrase most present in a statement, for the template."""
    doc_l = (doc_text or "").lower()
    ranked = sorted(candidates, key=lambda c: (c.lower() in doc_l, len(c)), reverse=True)
    for c in ranked:
        if c.strip():
            return c.strip()
    return fallback


def _adapt_text(meta: DocMeta, profile: StudentProfile) -> str:
    interest = _pick_phrase(profile.interests or profile.skills, meta.statement, "this area")
    skill = _pick_phrase(profile.skills or profile.interests, meta.statement, "your background")
    snippet = re.sub(r"\s+", " ", meta.statement or "").strip()
    if len(snippet) > 320:
        snippet = snippet[:317].rstrip() + "…"
    return (
        f"This matches your interest in {interest} and experience with {skill}. "
        f"Based on: “{meta.title}” (Project ID: {meta.project_id}). {snippet}"
    )


# --------------------------------------------------------------------------- #
# core
# --------------------------------------------------------------------------- #
def _student_vector(art: ModelArtifacts, text: str) -> sparse.csr_matrix:
    return normalize(art.vectorizer.transform([text]))


def _term_drivers(
    art: ModelArtifacts, student_vec: sparse.csr_matrix, doc_row: int, top: int = 6
) -> list[dict[str, Any]]:
    doc_vec = art.doc_matrix[doc_row]
    sv = student_vec.tocoo()
    contrib: list[tuple[str, float]] = []
    doc_dense = doc_vec.toarray().ravel()
    feats = art.vectorizer.get_feature_names_out()
    for idx, val in zip(sv.col, sv.data):
        overlap = float(val) * float(doc_dense[idx])
        if overlap > 0:
            contrib.append((feats[idx], overlap))
    contrib.sort(key=lambda x: x[1], reverse=True)
    total = sum(c for _, c in contrib) or 1.0
    return [
        {"term": t, "contribution": round(c, 4), "share": round(c / total, 3)}
        for t, c in contrib[:top]
    ]


def _cluster_distribution(art: ModelArtifacts, sims: np.ndarray) -> list[dict[str, Any]]:
    exp = np.exp((sims - sims.max()) * 8.0)
    soft = exp / exp.sum()
    return [
        {
            "cluster_id": int(c),
            "label": art.cluster_label(int(c)),
            "similarity": round(float(sims[c]), 4),
            "share": round(float(soft[c]), 3),
            "size": art.cluster_sizes.get(int(c), 0),
        }
        for c in np.argsort(sims)[::-1]
    ]


def _mmr(
    candidate_rows: list[int],
    relevance: dict[int, float],
    doc_matrix: sparse.csr_matrix,
    k: int,
    lam: float,
) -> list[int]:
    selected: list[int] = []
    pool = list(candidate_rows)
    while pool and len(selected) < k:
        best_row, best_val = None, -1e9
        for row in pool:
            if selected:
                sims = (doc_matrix[row] @ doc_matrix[selected].T).toarray().ravel()
                diversity = float(sims.max())
            else:
                diversity = 0.0
            val = lam * relevance[row] - (1 - lam) * diversity
            if val > best_val:
                best_row, best_val = row, val
        selected.append(best_row)
        pool.remove(best_row)
    return selected


def recommend(
    art: ModelArtifacts,
    profile: StudentProfile,
    *,
    route_threshold: float,
    serendipity: int,
    weights: dict[str, float],
    mmr_lambda: float,
    top_k: int,
    band_strong: float,
    band_moderate: float,
    exclude_project_ids: set[str] | None = None,
) -> RecResult:
    exclude_project_ids = exclude_project_ids or set()
    query = correct_typos(profile.query_text(), art.unigram_vocab())
    student_vec = _student_vector(art, query)

    weights_doc = (
        f"composite = {weights['relevance']:.2f}*relevance + "
        f"{weights['feasibility']:.2f}*feasibility + {weights['faculty']:.2f}*faculty_match. "
        f"relevance = cosine(student TF-IDF, statement TF-IDF) / {REL_SCALE:.2f}, capped at 1 "
        "(a fixed scale, so nothing ever displays as a full or perfect match). "
        "faculty_match is fixed at 0 until real preference data exists. "
        f"{FEASIBILITY_DOC}"
    )

    # --- no usable signal ------------------------------------------------- #
    if student_vec.nnz == 0:
        return RecResult(
            mode="no_signal",
            message=(
                "None of the words in your profile appear in our current corpus vocabulary, "
                "so we can't compute a meaningful match. Add a few more concrete skills or "
                "interests (tools, techniques, problem domains) and try again."
            ),
            routed_cluster=None,
            cluster_confidence=0.0,
            cluster_distribution=[],
            scoring_formula=weights_doc,
            weights=weights,
            recommendations=[],
        )

    # --- route ---------------------------------------------------------- #
    cluster_sims = np.asarray(student_vec @ art.centroids_unit.T).ravel()
    top_cluster = int(np.argmax(cluster_sims))
    cluster_confidence = float(cluster_sims[top_cluster])
    distribution = _cluster_distribution(art, cluster_sims)
    routed = cluster_confidence >= route_threshold

    doc_sims_all = np.asarray((student_vec @ art.doc_matrix.T).todense()).ravel()

    if routed:
        # Rank within the top cluster, plus any *near-tie* cluster (>= 85% of the top
        # centroid similarity, at most one extra) since profiles here often straddle
        # two quantum subdomains - then a small cross-cluster sample for serendipity.
        near = [
            int(c) for c in np.argsort(cluster_sims)[::-1][1:]
            if cluster_sims[c] >= 0.72 * cluster_confidence
        ][:1]
        routed_clusters = [int(top_cluster), *near]
        in_cluster = [i for i, c in enumerate(art.doc_clusters) if c in routed_clusters]
        others = [i for i in range(len(art.doc_ids)) if i not in set(in_cluster)]
        others_sorted = sorted(others, key=lambda i: doc_sims_all[i], reverse=True)
        serendipity_rows = set(others_sorted[:serendipity])
        candidate_rows = in_cluster + list(serendipity_rows)
        mode = "routed"
        label_list = " + ".join(f"“{art.cluster_label(c)}”" for c in routed_clusters)
        message = (
            f"Routed to {label_list} ({len(in_cluster)} statements) with routing confidence "
            f"{cluster_confidence:.3f}"
            + (
                f", plus {len(serendipity_rows)} cross-cluster pick(s) for breadth."
                if serendipity_rows
                else "."
            )
        )
    else:
        routed_clusters = []
        serendipity_rows = set()
        candidate_rows = list(range(len(art.doc_ids)))
        mode = "low_confidence"
        message = (
            "We don't have enough matching problem statements in your area yet. "
            f"The strongest cluster match is only {cluster_confidence:.3f} (below the "
            f"{route_threshold:.3f} routing threshold), so instead of forcing a match we're "
            "showing the closest available statements with their real similarity scores. "
            "Treat these as weak leads, not strong recommendations."
        )

    # --- filter + score ------------------------------------------------- #
    pool = [r for r in candidate_rows if art.docs_meta[r].project_id not in exclude_project_ids]
    # Fixed-scale relevance: cosine / REL_SCALE, clamped to 1. A fixed scale (not
    # min-max) keeps the weights meaningful without ever manufacturing a "1.0 / perfect
    # match" for whichever item happens to top the list.
    scored: dict[int, float] = {}
    for row in pool:
        meta = art.docs_meta[row]
        rel_norm = min(1.0, float(doc_sims_all[row]) / REL_SCALE)
        feas = feasibility_score(meta.statement)
        composite = (
            weights["relevance"] * rel_norm
            + weights["feasibility"] * feas
            + weights["faculty"] * 0.0
        )
        scored[row] = composite

    if not scored:
        return RecResult(
            mode="low_confidence" if routed else mode,
            message="Every candidate statement was filtered out by your current constraints.",
            routed_cluster=top_cluster if routed else None,
            routed_clusters=routed_clusters,
            cluster_confidence=round(cluster_confidence, 4),
            cluster_distribution=distribution,
            scoring_formula=weights_doc,
            weights=weights,
            recommendations=[],
        )

    ranked_rows = sorted(scored, key=lambda r: scored[r], reverse=True)[: max(top_k * 4, 20)]
    picked = _mmr(ranked_rows, scored, art.doc_matrix, top_k, mmr_lambda)
    sim_rank = {r: i for i, r in enumerate(sorted(scored, key=lambda r: doc_sims_all[r], reverse=True))}

    recs: list[Rec] = []
    for pos, row in enumerate(picked, start=1):
        meta = art.docs_meta[row]
        sim = float(doc_sims_all[row])
        drivers = _term_drivers(art, student_vec, row)
        item_cluster = int(art.doc_clusters[row])
        if pos == 1:
            note = "closest match to your profile"
        elif row in serendipity_rows or item_cluster not in routed_clusters:
            note = f"cross-domain pick from the “{art.cluster_label(item_cluster)}” cluster"
        elif sim_rank.get(row, 99) >= 2:
            note = "kept for spread (MMR), not just raw score"
        else:
            note = ""
        recs.append(
            Rec(
                rank=pos,
                project_id=meta.project_id,
                title=meta.title,
                statement=meta.statement,
                adapted_text=_adapt_text(meta, profile),
                cluster_id=int(art.doc_clusters[row]),
                cluster_label=art.cluster_label(int(art.doc_clusters[row])),
                similarity=round(sim, 4),
                composite_score=round(scored[row], 4),
                feasibility=round(feasibility_score(meta.statement), 3),
                confidence_band=_confidence_band(sim, band_strong, band_moderate),
                diversity_note=note,
                explanation={
                    "cosine_similarity": round(sim, 4),
                    "feasibility": round(feasibility_score(meta.statement), 3),
                    "feasibility_basis": f"statement length = {len(meta.statement or '')} chars",
                    "composite_score": round(scored[row], 4),
                    "weights": weights,
                    "top_term_drivers": drivers,
                    "routing": {
                        "mode": mode,
                        "routed_clusters": routed_clusters,
                        "cluster_confidence": round(cluster_confidence, 4),
                        "threshold": route_threshold,
                    },
                },
            )
        )

    if mode == "low_confidence" and recs and recs[0].similarity >= band_strong:
        message += (
            f" (Result #{recs[0].rank} is nonetheless a close individual match — cosine "
            f"{recs[0].similarity:.3f}. The low confidence is about overall domain coverage, "
            "not that specific statement.)"
        )

    return RecResult(
        mode=mode,
        message=message,
        routed_cluster=top_cluster if routed else None,
        routed_clusters=routed_clusters,
        cluster_confidence=round(cluster_confidence, 4),
        cluster_distribution=distribution,
        scoring_formula=weights_doc,
        weights=weights,
        recommendations=recs,
    )


# --------------------------------------------------------------------------- #
# refinement  (rule-based constraint parsing - no LLM)
# --------------------------------------------------------------------------- #
_NEG_PAT = re.compile(
    r"\b(?:no|not|non|avoid|without|exclude|drop|skip|remove|less)\b[ -]*", re.IGNORECASE
)
_POS_PAT = re.compile(
    r"\b(?:more|show me more|focus on|prefer|only|prioriti[sz]e|want)\b[ -]*", re.IGNORECASE
)
_STOP = {
    "the", "a", "an", "of", "and", "or", "to", "for", "with", "on", "in", "me",
    "please", "ideas", "idea", "project", "projects", "statement", "statements",
    "based", "kind", "type", "results", "result", "them", "that", "this",
    # first-person / conversational filler - the chat UI feeds whole sentences
    # ("I know Python and I'm interested in...") into this parser, not just
    # short constraint phrases, so filler needs to be stripped before it
    # gets mistaken for a topic to boost or avoid.
    "i", "im", "i'm", "ive", "i've", "id", "i'd", "know", "knows", "knowing",
    "am", "is", "are", "was", "were", "be", "been", "being", "my", "mine",
    "have", "has", "had", "want", "wants", "would", "like", "likes", "about",
    "into", "interested", "interest", "interests", "skill", "skills",
    "experience", "background", "also", "really", "just", "so", "very",
}


@dataclass
class RefineParse:
    negative: list[str]
    positive: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_refinement(text: str, vocabulary: set[str] | None = None) -> RefineParse:
    text = correct_typos(text.strip(), vocabulary)
    negative: list[str] = []
    positive: list[str] = []
    # polarity carries across "and"/comma-joined clauses that have no marker of
    # their own: "avoid AR/VR and simulation" -> both negative.
    carried = "positive"

    for chunk in re.split(r"[,;]|\band\b|\bbut\b", text, flags=re.IGNORECASE):
        chunk = chunk.strip()
        if not chunk:
            continue
        neg = bool(_NEG_PAT.search(chunk))
        pos = bool(_POS_PAT.search(chunk))
        cleaned = _POS_PAT.sub("", _NEG_PAT.sub("", chunk)).strip()
        keywords = [w for w in _tokens(cleaned) if w not in _STOP and len(w) > 2]
        # keep short multi-word phrases too (e.g. "ar/vr", "web based") - built
        # from the raw text (so characters like "/" survive, unlike _tokens()),
        # with filler words trimmed from either end so "I know Python" yields
        # "python", not the whole sentence.
        raw_phrase = re.sub(r"[^a-z0-9 /+-]", "", cleaned.lower()).strip()
        phrase_parts = [w for w in raw_phrase.split() if w not in _STOP]
        phrase = " ".join(phrase_parts)
        target = ([phrase] if 0 < len(phrase_parts) <= 3 else []) + keywords
        target = list(dict.fromkeys(t for t in target if t))
        if not target:
            continue

        if neg and not pos:
            polarity = "negative"
        elif pos and not neg:
            polarity = "positive"
        else:
            polarity = carried  # no explicit marker -> inherit
        carried = polarity

        (negative if polarity == "negative" else positive).extend(target)

    return RefineParse(
        negative=list(dict.fromkeys(negative)),
        positive=list(dict.fromkeys(positive)),
    )


def refine(
    art: ModelArtifacts,
    profile: StudentProfile,
    constraint_text: str,
    *,
    route_threshold: float,
    serendipity: int,
    weights: dict[str, float],
    mmr_lambda: float,
    top_k: int,
    band_strong: float,
    band_moderate: float,
) -> tuple[RecResult, RefineParse]:
    parse = parse_refinement(constraint_text, art.unigram_vocab())

    augmented = StudentProfile(
        skills=list(profile.skills),
        interests=list(profile.interests) + parse.positive * 2,  # upweight positives
        prior_projects=profile.prior_projects,
        tech_comfort=profile.tech_comfort,
        preferred_outcome=profile.preferred_outcome,
    )

    result = recommend(
        art,
        augmented,
        route_threshold=route_threshold,
        # A refine() call always carries explicit intent from the user's own
        # words - unlike a cold-start recommend(), padding the results with
        # cross-cluster "breadth" picks here means silently mixing in
        # off-topic statements (e.g. logistics content when someone asked
        # specifically for "the medical field"). Keep results in-domain.
        serendipity=0,
        weights=weights,
        mmr_lambda=mmr_lambda,
        top_k=max(top_k * 3, 12),
        band_strong=band_strong,
        band_moderate=band_moderate,
    )

    if parse.negative:
        kept: list[Rec] = []
        for rec in result.recommendations:
            hay = f"{rec.title} {rec.statement}".lower()
            if any(neg in hay for neg in parse.negative):
                continue
            kept.append(rec)
        result.recommendations = kept

    for i, rec in enumerate(result.recommendations[:top_k], start=1):
        rec.rank = i
    result.recommendations = result.recommendations[:top_k]
    result.message = (
        f"Refined with constraint: “{constraint_text.strip()}”. "
        f"Excluded terms: {parse.negative or 'none'}. Boosted terms: {parse.positive or 'none'}. "
        + result.message
    )
    return result, parse
