"""Backfill ``problem_statements.domain`` for rows that arrived without one.

Rules live in ``app.ml.domains.infer_domain`` (Project-ID code for the generated
batch, quantum content -> Quantum Computing, else a keyword vote). Every
decision, including rows left unassigned, is written to a CSV log.

Dry run by default - nothing is written to the database without ``--apply``.

    python -m scripts.assign_domains [--apply] [--log path/to/log.csv]
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, update  # noqa: E402

from app.config import BACKEND_DIR  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.ml.domains import infer_domain  # noqa: E402
from app.models import ProblemStatement  # noqa: E402


def _rule_kind(rule: str, domain: str | None) -> str:
    """Collapse a per-row rule string into a summary bucket."""
    if domain is None:
        return f"unassigned: {rule.split(' [')[0].split(' (')[0]}"
    if rule.startswith("keywords"):
        return "keyword vote"
    if rule.endswith("quantum terms in statement"):
        return "quantum terms in statement"
    return rule


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the assignments to the database")
    ap.add_argument("--log", help="CSV log path (default: backend/data/domain_backfill_<utc>.csv)")
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = Path(args.log) if args.log else BACKEND_DIR / "data" / f"domain_backfill_{stamp}.csv"

    db = SessionLocal()
    try:
        rows = db.scalars(
            select(ProblemStatement).where(ProblemStatement.domain.is_(None)).order_by(ProblemStatement.id)
        ).all()
        decisions = []
        for r in rows:
            domain, rule = infer_domain(r.project_id, r.title, r.statement)
            decisions.append((r, domain, rule))

        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "project_id", "source_batch", "is_flagged", "title", "assigned_domain", "rule"])
            for r, domain, rule in decisions:
                w.writerow([r.id, r.project_id, r.source_batch, r.is_flagged,
                            (r.title or "")[:120], domain or "", rule])

        assigned = [(r, d) for r, d, _ in decisions if d]
        print(f"rows with no domain: {len(rows)}  ->  assigned: {len(assigned)}, "
              f"left unassigned: {len(rows) - len(assigned)}")
        for domain, n in Counter(d for _, d in assigned).most_common():
            print(f"   {domain}: {n}")
        rule_kinds = Counter(_rule_kind(rule, d) for _, d, rule in decisions)
        print("by rule:")
        for rule, n in rule_kinds.most_common():
            print(f"   {rule}: {n}")
        print(f"log: {log_path}")

        if not args.apply:
            print("dry run - database unchanged (rerun with --apply to write)")
            return 0

        for r, domain in assigned:
            # guard on IS NULL so a label set by hand in the meantime is never overwritten
            db.execute(
                update(ProblemStatement)
                .where(ProblemStatement.id == r.id, ProblemStatement.domain.is_(None))
                .values(domain=domain)
            )
        db.commit()
        print(f"applied {len(assigned)} domain assignments")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
