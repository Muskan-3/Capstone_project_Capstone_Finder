"""Bulk-import a problem-statement CSV into the corpus and retrain.

Headers are matched case-insensitively through the same aliases as the admin
upload (ProjectID / Title / Problem Statement required; domain / field /
difficulty / source optional), and every row goes through the same ``clean()``
flagging rules. Rows whose ProjectID already exists in the database are
skipped, so re-running on the same file inserts nothing. All inserts happen in
one transaction; retraining then runs through ``app.training.retrain``.

    python -m scripts.import_corpus [path/to/file.csv] [--batch NAME] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from sqlalchemy import func, insert, select  # noqa: E402

from app.config import BACKEND_DIR  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.ml.ingest import clean, project_table  # noqa: E402
from app.models import ProblemStatement  # noqa: E402
from app.training import retrain  # noqa: E402

DEFAULT_CSV = BACKEND_DIR / "data" / "problems_corpus_v2.csv"


def read_rows(path: Path) -> list[list[object]]:
    # dtype=str + keep_default_na=False: IDs like "007" stay text, blanks stay "",
    # and clean() decides what counts as missing - same as the csv upload path
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return project_table(list(df.columns), df.values.tolist())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    ap.add_argument("--batch", help="source_batch tag (default: the file name without extension)")
    ap.add_argument("--dry-run", action="store_true", help="report counts, write nothing")
    args = ap.parse_args()

    path = Path(args.csv)
    batch = args.batch or path.stem
    rows, report = clean(read_rows(path), source=path.name, sheet="csv", source_batch=batch)

    init_db()  # adds any missing nullable columns, same as API startup
    db = SessionLocal()
    try:
        known = set(db.scalars(select(ProblemStatement.project_id)).all())
        # an in-file duplicate (X-B) is skipped along with X when X is already stored
        fresh = [r for r in rows if r.project_id not in known and r.original_project_id not in known]
        skipped = len(rows) - len(fresh)
        flags = Counter(p for r in fresh if r.flag_reason for p in r.flag_reason.split("; "))

        print(f"{path.name}: {len(rows)} rows -> batch {batch!r}")
        print(f"   inserted: {len(fresh)}{' (dry run - not written)' if args.dry_run else ''}")
        print(f"   skipped (ProjectID already in DB): {skipped}")
        print(f"   flagged: {sum(1 for r in fresh if r.is_flagged)}")
        for reason, n in sorted(flags.items()):
            print(f"      {reason}: {n}")
        if args.dry_run:
            return 0

        if fresh:
            db.execute(
                insert(ProblemStatement),
                [
                    {
                        "project_id": r.project_id,
                        "title": r.title,
                        "statement": r.statement,
                        "is_flagged": r.is_flagged,
                        "flag_reason": r.flag_reason,
                        "source_batch": batch,
                        "original_project_id": r.original_project_id,
                        "domain": r.domain,
                        "field": r.field,
                        "difficulty": r.difficulty,
                        "source": r.source,
                    }
                    for r in fresh
                ],
            )
        db.commit()

        mv = retrain(db, notes=f"import {path.name} ({len(fresh)} new rows)")
        print(f"trained model v{mv.version}: corpus={mv.corpus_size}, k={mv.cluster_count}, "
              f"silhouette={mv.silhouette:.4f}")

        # rows the model trained on are exactly the ones retrain() gave a cluster
        in_model = ProblemStatement.cluster_id.is_not(None)
        by_domain = db.execute(
            select(ProblemStatement.domain, func.count())
            .where(in_model)
            .group_by(ProblemStatement.domain)
            .order_by(func.count().desc())
        ).all()
        print("per-domain counts (rows in the trained corpus):")
        for domain, n in by_domain:
            print(f"   {domain or '(no domain)'}: {n}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
