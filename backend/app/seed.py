"""Seed the database from the source workbook and train the first model.

Idempotent: running it again on a populated database is a no-op unless ``--force``.

    python -m app.seed [--force]
"""

from __future__ import annotations

import sys

from sqlalchemy import func, select

from .db import SessionLocal, init_db
from .config import settings
from .ml.ingest import clean, read_source
from .models import ProblemStatement
from .training import retrain


def seed(force: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        count = db.scalar(select(func.count()).select_from(ProblemStatement)) or 0
        if count and not force:
            print(f"database already has {count} problem statements - skipping seed "
                  f"(use --force to wipe and reseed)")
            return
        if force:
            db.query(ProblemStatement).delete()
            db.commit()

        if not settings.source_workbook.exists():
            raise SystemExit(f"source workbook not found: {settings.source_workbook}")

        sheet, raw = read_source(settings.source_workbook)
        rows, report = clean(
            raw, source=settings.source_workbook.name, sheet=sheet, source_batch="initial"
        )
        for r in rows:
            db.add(
                ProblemStatement(
                    project_id=r.project_id,
                    title=r.title,
                    statement=r.statement,
                    is_flagged=r.is_flagged,
                    flag_reason=r.flag_reason,
                    source_batch="initial",
                    original_project_id=r.original_project_id,
                )
            )
        db.commit()
        print(f"ingested {report.total_rows} rows "
              f"({report.active_rows} active, {report.flagged_rows} flagged)")
        for reason, n in sorted(report.flag_counts.items()):
            print(f"   {reason}: {n}")

        mv = retrain(db, notes="initial seed")
        print(f"trained model v{mv.version}: k={mv.cluster_count}, "
              f"silhouette={mv.silhouette:.4f}, corpus={mv.corpus_size}")
    finally:
        db.close()


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
