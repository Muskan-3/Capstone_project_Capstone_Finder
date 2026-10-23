"""Route by domain -> gate -> rank -> diversify -> explain -> adapt text.

Pure functions over a ``ModelArtifacts`` snapshot and a student profile. No
database access, no text generation - the shown text is the real corpus
statement wrapped in a fixed rationale template, and every item carries its
real ``project_id``. Scores are kept for ranking, gating and the stored
explanation; the student-facing UI does not display them.
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

from .domains import DOMAINS, keyword_hits
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

# cosine similarity that maps to a "full" relevance bar in the composite score.
# A fixed scale (not min-max) keeps the weights meaningful without manufacturing
# a "perfect match" for whichever item happens to top the list.
REL_SCALE = 0.50
# the document-level gate averages this many best in-domain similarities
GATE_TOP_N = 3
# topic concentration = largest single-domain share among this many nearest documents
CONCENTRATION_TOP_N = 10


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
    domain: str | None
    similarity: float          # raw cosine, student vs statement - internal, never shown to students
    composite_score: float     # weighted blend actually used for ranking
    feasibility: float
    diversity_note: str
    explanation: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Routing:
    domains: list[str]                       # ranking happens only here; [] = nothing to rank in
    source: str                              # "keyword" | "classifier" | "unrouted"
    keyword_hits: dict[str, list[str]]
    probabilities: list[dict[str, Any]]      # classifier output, best first (top 5)


@dataclass
class RecResult:
    mode: str                  # "routed" | "off_topic" | "no_signal"
    message: str
    routed_domains: list[str]
    routing_source: str
    domain_probabilities: list[dict[str, Any]]
    gate_score: float          # mean of the top-3 cosine similarities inside the routed domain(s)
    gate_threshold: float
    scoring_formula: str
    weights: dict[str, float]
    recommendations: list[Rec]
    suggested_domains: list[str] = field(default_factory=list)
    # classifier-routed requests only: largest one-domain share of the 10 nearest documents
    topic_concentration: float | None = None

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


def available_domains(art: ModelArtifacts) -> list[str]:
    """Domains the active model can route to, in the canonical display order."""
    if not art.has_domain_router():
        return []
    present = set(art.domain_sizes)
    return [d for d in DOMAINS if d in present] + sorted(present - set(DOMAINS))


def route_domains(
    art: ModelArtifacts, text: str, vec: sparse.csr_matrix, *, split_ratio: float
) -> Routing:
    """Keyword map first; the TF-IDF + logistic-regression classifier only when
    no keyword fires. Two domains when the top two are tied (keywords) or the
    runner-up has at least ``split_ratio`` of the leader's probability."""
    if not art.has_domain_router():
        return Routing([], "unrouted", {}, [])

    probs: list[dict[str, Any]] = []
    if art.domain_clf is not None and vec.nnz:
        p = art.domain_clf.predict_proba(vec)[0]
        probs = [
            {"domain": str(art.domain_clf.classes_[i]), "probability": round(float(p[i]), 4)}
            for i in np.argsort(p)[::-1]
        ]
    prob_of = {x["domain"]: x["probability"] for x in probs}

    present = set(art.domain_sizes)
    all_hits = keyword_hits(text)
    hits = {d: kws for d, kws in all_hits.items() if d in present}
    if hits:
        ranked = sorted(hits, key=lambda d: (len(hits[d]), prob_of.get(d, 0.0)), reverse=True)
        tied = [d for d in ranked if len(hits[d]) == len(hits[ranked[0]])]
        return Routing(tied[:2], "keyword", hits, probs[:5])
    if all_hits:
        # explicitly asked for a domain this corpus has no statements in: no
        # domains to rank in (recommend() answers off-topic), never a classifier guess
        return Routing([], "keyword", all_hits, probs[:5])

    if probs:
        domains = [probs[0]["domain"]]
        if len(probs) > 1 and probs[1]["probability"] >= split_ratio * probs[0]["probability"]:
            domains.append(probs[1]["domain"])
        return Routing(domains, "classifier", {}, probs[:5])
    return Routing([], "unrouted", {}, [])


def _no_match(
    art: ModelArtifacts,
    mode: str,
    routing: Routing,
    gate_score: float,
    gate_threshold: float,
    weights_doc: str,
    weights: dict[str, float],
    concentration: float | None = None,
) -> RecResult:
    suggestions = available_domains(art)
    message = "I couldn't find projects that match that."
    if suggestions:
        message += f" Try one of these domains: {', '.join(suggestions)}."
    return RecResult(
        mode=mode,
        message=message,
        routed_domains=routing.domains,
        routing_source=routing.source,
        domain_probabilities=routing.probabilities,
        gate_score=round(gate_score, 4),
        gate_threshold=gate_threshold,
        scoring_formula=weights_doc,
        weights=weights,
        recommendations=[],
        suggested_domains=suggestions,
        topic_concentration=concentration,
    )


def recommend(
    art: ModelArtifacts,
    profile: StudentProfile,
    *,
    gate_threshold: float,
    concentration_min: float,
    split_ratio: float,
    weights: dict[str, float],
    mmr_lambda: float,
    top_k: int,
    exclude_project_ids: set[str] | None = None,
    route_text: str | None = None,
) -> RecResult:
    """Route to a domain, gate on document evidence, then rank + diversify inside it.

    The gate has two parts. Every request needs the mean of its top-3 cosine
    similarities inside the routed domain(s) to reach ``gate_threshold``. A
    request routed by the classifier (no keyword fired) must also hit a coherent
    topic: at least ``concentration_min`` of its 10 nearest documents in one
    domain. Off-topic asks ("poetry writing") match a few documents in many
    domains, so a classifier guess alone is not trusted for them.

    ``route_text`` is what the student actually asked for (the chat message);
    routing and the gate use it, ranking uses the whole profile. Defaults to
    the profile text.
    """
    exclude_project_ids = exclude_project_ids or set()
    vocab = art.unigram_vocab()
    query = correct_typos(profile.query_text(), vocab)
    route_query = correct_typos(route_text, vocab) if route_text else query
    student_vec = _student_vector(art, query)
    route_vec = _student_vector(art, route_query)

    weights_doc = (
        f"composite = {weights['relevance']:.2f}*relevance + "
        f"{weights['feasibility']:.2f}*feasibility + {weights['faculty']:.2f}*faculty_match. "
        f"relevance = cosine(student TF-IDF, statement TF-IDF) / {REL_SCALE:.2f}, capped at 1. "
        "faculty_match is fixed at 0 until real preference data exists. "
        f"{FEASIBILITY_DOC}"
    )

    # --- route ---------------------------------------------------------- #
    routing = route_domains(art, route_query, route_vec, split_ratio=split_ratio)
    if route_vec.nnz == 0 and routing.source != "keyword":
        return _no_match(art, "no_signal", routing, 0.0, gate_threshold, weights_doc, weights)
    if not routing.domains:
        # nothing to rank in: a keyword for a domain this corpus lacks, a
        # single-domain corpus (no classifier) with no keyword hit, or an
        # artifact trained before domain routing. Never fall back to the
        # whole corpus - that is exactly the forced match the gate prevents.
        return _no_match(art, "off_topic", routing, 0.0, gate_threshold, weights_doc, weights)

    routed = set(routing.domains)
    candidate_rows = [i for i, d in enumerate(art.doc_domains) if d in routed]

    # --- gate: is there real document evidence in the routed domain? ------ #
    route_sims = np.asarray((route_vec @ art.doc_matrix.T).todense()).ravel()
    best = np.sort(route_sims[candidate_rows])[::-1][:GATE_TOP_N] if candidate_rows else []
    gate_score = float(np.mean(best)) if len(best) else 0.0
    concentration: float | None = None
    if routing.source == "classifier":
        nearest = np.argsort(route_sims)[::-1][:CONCENTRATION_TOP_N]
        shares: dict[str, int] = {}
        for i in nearest:
            d = art.doc_domains[i] or ""
            shares[d] = shares.get(d, 0) + 1
        concentration = max(shares.values()) / len(nearest)
    if gate_score < gate_threshold or (concentration is not None and concentration < concentration_min):
        return _no_match(art, "off_topic", routing, gate_score, gate_threshold, weights_doc, weights,
                         concentration)

    # --- filter + score ------------------------------------------------- #
    doc_sims_all = np.asarray((student_vec @ art.doc_matrix.T).todense()).ravel()
    pool = [r for r in candidate_rows if art.docs_meta[r].project_id not in exclude_project_ids]
    scored: dict[int, float] = {}
    for row in pool:
        meta = art.docs_meta[row]
        rel_norm = min(1.0, float(doc_sims_all[row]) / REL_SCALE)
        scored[row] = (
            weights["relevance"] * rel_norm
            + weights["feasibility"] * feasibility_score(meta.statement)
            + weights["faculty"] * 0.0
        )

    label = " + ".join(f"“{d}”" for d in routing.domains)
    message = (
        f"Matched {label} by {routing.source}"
        + (f" ({', '.join(kw for kws in routing.keyword_hits.values() for kw in kws)})"
           if routing.keyword_hits else "")
        + "."
    )
    if not scored:
        message = f"{message} Every matching statement was filtered out by your current constraints."

    ranked_rows = sorted(scored, key=lambda r: scored[r], reverse=True)[: max(top_k * 4, 20)]
    picked = _mmr(ranked_rows, scored, art.doc_matrix, top_k, mmr_lambda)
    sim_rank = {r: i for i, r in enumerate(sorted(scored, key=lambda r: doc_sims_all[r], reverse=True))}

    recs: list[Rec] = []
    for pos, row in enumerate(picked, start=1):
        meta = art.docs_meta[row]
        sim = float(doc_sims_all[row])
        if pos == 1:
            note = "closest match to your request"
        elif len(routing.domains) > 1 and art.doc_domains[row] != routing.domains[0]:
            note = f"from the related {art.doc_domains[row]} domain"
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
                domain=art.doc_domains[row],
                similarity=round(sim, 4),
                composite_score=round(scored[row], 4),
                feasibility=round(feasibility_score(meta.statement), 3),
                diversity_note=note,
                explanation={
                    "cosine_similarity": round(sim, 4),
                    "feasibility": round(feasibility_score(meta.statement), 3),
                    "feasibility_basis": f"statement length = {len(meta.statement or '')} chars",
                    "composite_score": round(scored[row], 4),
                    "weights": weights,
                    "top_term_drivers": _term_drivers(art, student_vec, row),
                    "routing": {
                        "domains": routing.domains,
                        "source": routing.source,
                        "keyword_hits": routing.keyword_hits,
                        "gate_score": round(gate_score, 4),
                        "gate_threshold": gate_threshold,
                        "topic_concentration": concentration,
                    },
                },
            )
        )

    return RecResult(
        mode="routed",
        message=message,
        routed_domains=routing.domains,
        routing_source=routing.source,
        domain_probabilities=routing.probabilities,
        gate_score=round(gate_score, 4),
        gate_threshold=gate_threshold,
        scoring_formula=weights_doc,
        weights=weights,
        recommendations=recs,
        topic_concentration=concentration,
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
    # the message adjusts the current results ("more X", "avoid Y", "focus on Z")
    # rather than making a fresh ask
    modifier: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_refinement(text: str, vocabulary: set[str] | None = None) -> RefineParse:
    text = correct_typos(text.strip(), vocabulary)
    negative: list[str] = []
    positive: list[str] = []
    # polarity carries across "and"/comma-joined clauses that have no marker of
    # their own: "avoid AR/VR and simulation" -> both negative.
    carried = "positive"
    modifier = False

    for chunk in re.split(r"[,;]|\band\b|\bbut\b", text, flags=re.IGNORECASE):
        chunk = chunk.strip()
        if not chunk:
            continue
        neg = bool(_NEG_PAT.search(chunk))
        pos = bool(_POS_PAT.search(chunk))
        modifier = modifier or neg or pos
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
        modifier=modifier,
    )


def refine(
    art: ModelArtifacts,
    profile: StudentProfile,
    constraint_text: str,
    *,
    gate_threshold: float,
    concentration_min: float,
    split_ratio: float,
    weights: dict[str, float],
    mmr_lambda: float,
    top_k: int,
) -> tuple[RecResult, RefineParse]:
    parse = parse_refinement(constraint_text, art.unigram_vocab())

    augmented = StudentProfile(
        skills=list(profile.skills),
        interests=list(profile.interests) + parse.positive * 2,  # upweight positives
        prior_projects=profile.prior_projects,
        tech_comfort=profile.tech_comfort,
        preferred_outcome=profile.preferred_outcome,
    )

    # What the routing + off-topic gate look at:
    #  - the message names a domain ("suggest a blockchain project", "more web-based")
    #    -> the message alone, so an explicit ask is never overridden by the profile
    #  - a modifier with no domain keyword ("more optimization, avoid AR/VR"), or
    #    nothing positive at all -> the profile plus the message: it adjusts the
    #    current context rather than asking about something new
    #  - otherwise a fresh ask ("cooking recipes") -> the message alone, judged as
    #    strictly as any cold query; the profile can't vouch for an off-topic ask
    # Negative terms never take part ("no web stuff" must not route to Web/Mobile).
    asked = " ".join(parse.positive)
    in_context = not asked or (parse.modifier and not keyword_hits(asked))

    result = recommend(
        art,
        augmented,
        gate_threshold=gate_threshold,
        concentration_min=concentration_min,
        split_ratio=split_ratio,
        weights=weights,
        mmr_lambda=mmr_lambda,
        top_k=max(top_k * 3, 12),
        route_text=None if in_context else asked,
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
