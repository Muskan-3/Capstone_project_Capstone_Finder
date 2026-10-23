"""Calibrate and evaluate domain routing + the document-level gate.

Trains a model *in memory* from the current active corpus (rows without a
stored domain are labelled by the same rules as scripts/assign_domains.py),
runs an on-topic / off-topic query set through ``recommend()``, calibrates the
gate thresholds (fewest false accepts + false rejects, widest margin), and
reports top-3 results with precision@3 per domain. Read-only: nothing is written to the
database and nothing is activated.

    python -m scripts.eval_routing [--gate 0.1] [--concentration 0.45] [--k-max 20]

Precision@3 is measured against the corpus ``domain`` labels: CSV-provided for
the v2 batch, keyword/ID-derived for the older rows - not human relevance
judgements.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.ml.pipeline import ModelArtifacts, train  # noqa: E402
from app.ml.recommender import StudentProfile, recommend  # noqa: E402
from app.training import _active_docs  # noqa: E402

WEB, AI, IOT, CYB, BC, CLOUD, NLP, CV, DA, CIV, MECH, EEE, CS, QC = (
    "Web/Mobile", "AI/ML", "IoT", "Cybersecurity", "Blockchain", "Cloud Computing", "NLP",
    "Computer Vision", "Data Analytics", "Civil Engineering", "Mechanical Engineering",
    "Electrical & Electronics", "Computer Science & IT", "Quantum Computing",
)

# query -> acceptable domains (first = the domain it is reported under)
ON_TOPIC: dict[str, tuple[str, ...]] = {
    # the 12 on-topic probes from the first run
    "website development": (WEB,),
    "mobile app": (WEB,),
    "IoT sensors project": (IOT,),
    "machine learning prediction": (AI,),
    "cybersecurity": (CYB,),
    "blockchain": (BC,),
    "chatbot NLP": (NLP,),
    "computer vision": (CV,),
    "data dashboard": (DA,),
    "cloud deployment": (CLOUD,),
    "civil engineering": (CIV,),
    "quantum cryptography": (QC, CYB),
    # 20 more, every domain covered; about half carry no routing keyword, so
    # they exercise the classifier fallback
    "react native fitness tracker": (WEB,),
    "arduino home automation": (IOT,),
    "smart contract voting system": (BC,),
    "phishing email detection": (CYB,),
    "network intrusion detection": (CYB,),
    "kubernetes autoscaling microservices": (CLOUD,),
    "sentiment analysis of tweets": (NLP,),
    "face recognition attendance system": (CV,),
    "sales forecasting with time series": (DA, AI),
    "earthquake resistant building design": (CIV,),
    "heat exchanger CFD analysis": (MECH,),
    "wind turbine blade aerodynamics": (MECH,),
    "solar inverter design": (EEE,),
    "battery management system for electric vehicles": (EEE,),
    "smart traffic routing system": (CS,),
    "healthcare data management platform": (CS,),
    "qubit error correction": (QC,),
    "variational quantum eigensolver for chemistry": (QC,),
    "deep learning for medical diagnosis": (AI,),
    "satellite image segmentation": (CV,),
}
OFF_TOPIC = ["cooking recipes", "poetry writing", "history of rome", "football",
             "weather today", "best pizza", "asdfgh"]

# everything recommend() needs except the gate threshold
KW = dict(
    split_ratio=settings.domain_split_ratio,
    weights={"relevance": settings.weight_relevance, "feasibility": settings.weight_feasibility,
             "faculty": settings.weight_faculty},
    mmr_lambda=settings.mmr_lambda,
    top_k=3,
)


def build_model(k_max: int | None = None) -> ModelArtifacts:
    db = SessionLocal()
    try:
        docs = _active_docs(db)
    finally:
        db.close()
    return train(
        docs, version=0, max_features=settings.tfidf_max_features, min_df=settings.tfidf_min_df,
        k_min=settings.kmeans_k_min, k_max=k_max or settings.kmeans_k_max,
        random_state=settings.random_state,
    )


class Signal:
    def __init__(self, gate: float, conc: float | None, domains: list[str], source: str):
        self.gate, self.conc, self.domains, self.source = gate, conc, domains, source


def signals(art: ModelArtifacts) -> dict[str, Signal]:
    """query -> gate inputs, measured with both gates switched off."""
    out = {}
    for q in [*ON_TOPIC, *OFF_TOPIC]:
        r = recommend(art, StudentProfile(interests=[q]), gate_threshold=-1.0,
                      concentration_min=-1.0, **KW)
        gate = r.gate_score if r.mode != "no_signal" else 0.0
        out[q] = Signal(gate, r.topic_concentration, r.routed_domains, r.routing_source)
    return out


def calibrate(on: list[float], off: list[float]) -> float:
    """Midpoint cut with the fewest errors (on-topic below it + off-topic at or
    above it); among equals, the widest margin to the nearest score."""
    vals = sorted(set(on) | set(off))
    cuts = [(a + b) / 2 for a, b in zip(vals, vals[1:])] or vals

    def errors(t: float) -> int:
        return sum(v < t for v in on) + sum(v >= t for v in off)

    return round(min(cuts, key=lambda t: (errors(t), -min(abs(t - v) for v in vals))), 3)


def accepted(sig: Signal, gate_t: float, conc_t: float | None) -> bool:
    if sig.source == "unrouted" and sig.gate == 0.0:
        return False
    conc_ok = conc_t is None or sig.conc is None or sig.conc >= conc_t
    return sig.gate >= gate_t and conc_ok


def errors_at(sig: dict[str, Signal], gate_t: float, conc_t: float | None) -> tuple[list[str], list[str]]:
    fr = [q for q in ON_TOPIC if not accepted(sig[q], gate_t, conc_t)]
    fa = [q for q in OFF_TOPIC if accepted(sig[q], gate_t, conc_t)]
    return fr, fa


def report(art: ModelArtifacts, gate_t: float | None, conc_t: float | None) -> None:
    print(f"trial model (in memory): corpus={art.corpus_size}, kmeans k={art.k} "
          f"(admin topic map only), router params={art.params['domain_router']}")
    print("domain sizes:", dict(sorted(art.domain_sizes.items(), key=lambda x: -x[1])))

    sig = signals(art)
    # (a) the document-level gate on its own, as first specified
    spec_t = calibrate([sig[q].gate for q in ON_TOPIC], [sig[q].gate for q in OFF_TOPIC])
    spec_fr, spec_fa = errors_at(sig, spec_t, None)
    # (b) + topic concentration for classifier-routed requests, then the gate
    # threshold re-calibrated on the combined decision
    clf_on = [sig[q].conc for q in ON_TOPIC if sig[q].conc is not None]
    clf_off = [sig[q].conc for q in OFF_TOPIC if sig[q].conc is not None]
    cal_conc = calibrate(clf_on, clf_off)
    vals = sorted({s.gate for s in sig.values()})
    cuts = [(a + b) / 2 for a, b in zip(vals, vals[1:])]
    cal_gate = round(min(cuts, key=lambda t: (sum(map(len, errors_at(sig, t, cal_conc))),
                                              -min(abs(t - v) for v in vals))), 3)
    gate_t = cal_gate if gate_t is None else gate_t
    conc_t = cal_conc if conc_t is None else conc_t
    fr, fa = errors_at(sig, gate_t, conc_t)

    print(f"\n== calibration ({len(ON_TOPIC)} on-topic, {len(OFF_TOPIC)} off-topic; in-sample)")
    print(f"  (a) doc gate alone:            threshold {spec_t}  ->  false rejects {len(spec_fr)}, "
          f"false accepts {len(spec_fa)} {spec_fa}")
    print(f"  (b) doc gate + concentration:  gate {cal_gate}, concentration {cal_conc}  ->  "
          f"false rejects {len(fr) if (gate_t, conc_t) == (cal_gate, cal_conc) else '-'}, "
          f"false accepts {len(fa) if (gate_t, conc_t) == (cal_gate, cal_conc) else '-'}")
    if (gate_t, conc_t) != (cal_gate, cal_conc):
        print(f"  evaluating at gate {gate_t}, concentration {conc_t}")

    print("\n  score per query (gate = mean top-3 cosine in routed domain; conc = classifier-routed only)")
    for label, qs in (("ON-TOPIC", list(ON_TOPIC)), ("OFF-TOPIC", OFF_TOPIC)):
        print(f"  {label}")
        for q in sorted(qs, key=lambda q: -sig[q].gate):
            s = sig[q]
            conc = f"{s.conc:.1f}" if s.conc is not None else "  -"
            wrong = "" if label == "OFF-TOPIC" or set(s.domains) & set(ON_TOPIC[q]) else "  WRONG-ROUTE"
            print(f"    gate {s.gate:.3f}  conc {conc}  {'accept' if accepted(s, gate_t, conc_t) else 'REJECT'}"
                  f"  {q!r:50} -> {' + '.join(s.domains) or '-'} [{s.source}]{wrong}")
    print(f"\n  false rejects: {len(fr)}/{len(ON_TOPIC)} {fr}")
    print(f"  false accepts: {len(fa)}/{len(OFF_TOPIC)} {fa}")
    wrong = [q for q in ON_TOPIC if not set(sig[q].domains) & set(ON_TOPIC[q])]
    print(f"  wrong routing (on-topic): {len(wrong)}/{len(ON_TOPIC)} {wrong}")

    print(f"\n== top 3 (gate {gate_t}, concentration {conc_t})")
    per_domain: dict[str, list[float]] = defaultdict(list)
    for q in [*ON_TOPIC, *OFF_TOPIC]:
        res = recommend(art, StudentProfile(interests=[q]), gate_threshold=gate_t,
                        concentration_min=conc_t, **KW)
        expected = ON_TOPIC.get(q)
        print(f"  {q!r}: {res.mode}, routed {' + '.join(res.routed_domains) or '-'}"
              f" [{res.routing_source}]" + ("" if expected else "  (off-topic)"))
        if not res.recommendations:
            print(f"      no projects - {res.message[:110]}")
        hits = 0
        for r in res.recommendations[:3]:
            ok = expected is None or r.domain in expected
            hits += ok
            print(f"    {'         ' if ok else 'MISMATCH '}{r.title[:66]!r} | {r.domain}")
        if expected and res.recommendations:
            per_domain[expected[0]].append(hits / min(3, len(res.recommendations)))

    print("\n== precision@3 per domain (vs corpus domain labels; rejected queries excluded)")
    for d, ps in sorted(per_domain.items(), key=lambda x: sum(x[1]) / len(x[1])):
        print(f"  {d:26} {sum(ps) / len(ps):.2f}  over {len(ps)} quer{'y' if len(ps) == 1 else 'ies'}")
    allp = [p for ps in per_domain.values() for p in ps]
    print(f"  {'overall':26} {sum(allp) / len(allp):.2f}  over {len(allp)} queries")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", type=float, help="evaluate at this gate threshold instead of the calibrated one")
    ap.add_argument("--concentration", type=float, help="evaluate at this concentration minimum")
    ap.add_argument("--k-max", type=int, help="KMeans k_max for the trial model (default: settings)")
    args = ap.parse_args()
    report(build_model(args.k_max), args.gate, args.concentration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
