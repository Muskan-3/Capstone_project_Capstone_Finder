"""Import the generated multi-domain problem statements into the corpus and retrain.

The generated CSV (domain, field, level, novelty, text, ..., score, reason) has no
ProjectID / Title columns, so it can't go through the admin upload as-is. This
script derives both, then runs every row through the same ``clean()`` rules as
the workbook. Rows whose review score is below ``--min-score`` are kept but
flagged ``low_quality_score`` - they land in the admin Needs Review queue
instead of the recommendation pool (flag, never drop).

    python -m scripts.import_generated [path/to/generated_scored.csv] [--min-score 5] [--replace]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.config import BACKEND_DIR  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.ml.ingest import clean  # noqa: E402
from app.models import ProblemStatement  # noqa: E402
from app.training import retrain  # noqa: E402

BATCH = "generated-v1"
DEFAULT_CSV = BACKEND_DIR / "data" / "generated_scored.csv"
DOMAIN_CODES = {
    "AI/ML": "AIML",
    "Cybersecurity": "CYB",
    "Civil Engineering": "CIV",
    "Electrical & Electronics": "EEE",
    "Mechanical Engineering": "MECH",
}
_PREFIX = re.compile(r"^How can we develop a practical engineering solution to ", re.IGNORECASE)
# after the prefix is stripped, the title is the core task before using/for/from/","
_CORE = re.compile(r"^(.+?)(?: using | from | for |,|\.|$)")


def split_text(text: str) -> tuple[str, str]:
    """Return (title, body). Question-style rows lose the boilerplate prefix and
    are titled by their core task; the rest are already title-like sentences."""
    stripped = _PREFIX.sub("", text)
    if stripped == text:
        return text.rstrip("."), text
    body = stripped[:1].upper() + stripped[1:].rstrip("?") + "."
    return _CORE.match(body).group(1).strip(), body


def build_rows(path: Path) -> tuple[list[list[object]], dict[int, tuple[int, str]]]:
    raw: list[list[object]] = []
    scores: dict[int, tuple[int, str]] = {}
    counters: dict[str, int] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for source_row, r in enumerate(csv.DictReader(f), start=2):
            # the shared question prefix is pure boilerplate; left in, it forms its own
            # KMeans cluster and drags cyber/AI rows away from their real topics
            title, body = split_text(re.sub(r"\s+", " ", r["text"]).strip())
            code = DOMAIN_CODES.get(r["domain"], "GEN")
            counters[code] = counters.get(code, 0) + 1
            pid = f"GEN-{code}-{counters[code]:03d}"
            # domain/level go into the statement so TF-IDF can match "civil", "mechanical" etc.
            statement = f"{body} Domain: {r['domain']} ({r['field']}). Level: {r['level']}."
            raw.append([pid, title, statement, source_row])
            scores[source_row] = (int(r["score"]), r["reason"])
    return raw, scores


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    ap.add_argument("--min-score", type=int, default=5)
    ap.add_argument("--replace", action="store_true", help=f"delete an existing {BATCH} batch first")
    args = ap.parse_args()

    path = Path(args.csv)
    raw, scores = build_rows(path)
    rows, report = clean(raw, source=path.name, sheet="csv", source_batch=BATCH)

    init_db()
    db = SessionLocal()
    try:
        existing = db.scalars(
            select(ProblemStatement).where(ProblemStatement.source_batch == BATCH)
        ).all()
        if existing and not args.replace:
            print(f"batch {BATCH!r} already has {len(existing)} rows - rerun with --replace")
            return 1
        for e in existing:
            db.delete(e)

        low = 0
        for r in rows:
            score, _ = scores[r.source_row]
            reason = r.flag_reason
            if score < args.min_score:
                reason = "; ".join(p for p in (reason, "low_quality_score") if p)
                low += 1
            db.add(
                ProblemStatement(
                    project_id=r.project_id,
                    title=r.title,
                    statement=r.statement,
                    is_flagged=reason is not None,
                    flag_reason=reason,
                    source_batch=BATCH,
                    original_project_id=r.original_project_id,
                )
            )
        db.commit()

        active = sum(1 for r in rows if not r.is_flagged and scores[r.source_row][0] >= args.min_score)
        print(f"imported {len(rows)} rows from {path.name} as batch {BATCH!r}")
        print(f"   active (score >= {args.min_score}): {active}")
        print(f"   flagged low_quality_score: {low}")
        for reason, n in sorted(report.flag_counts.items()):
            print(f"   flagged {reason}: {n}")

        mv = retrain(db, notes=f"import {BATCH} (min score {args.min_score})")
        print(f"trained model v{mv.version}: k={mv.cluster_count}, "
              f"silhouette={mv.silhouette:.4f}, corpus={mv.corpus_size}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
