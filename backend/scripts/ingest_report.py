"""Section 11, step 1 - run the cleaning rules against the real spreadsheet and
print a report. No database, no model. Just: does ingestion flag the right rows?

    python -m scripts.ingest_report [path/to/workbook.xlsx]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.ml.ingest import clean, read_source  # noqa: E402


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.source_workbook
    if not path.exists():
        print(f"!! source workbook not found: {path}")
        return 1

    sheet, raw = read_source(path)
    rows, report = clean(raw, source=path.name, sheet=sheet, source_batch="initial")

    print("=" * 78)
    print(f"  INGEST REPORT  -  {path.name}")
    print(f"  sheet: {sheet}")
    print("=" * 78)
    print(f"  total rows parsed .......... {report.total_rows}")
    print(f"  active (recommendable) ..... {report.active_rows}")
    print(f"  flagged (needs review) ..... {report.flagged_rows}")
    print("  flag breakdown:")
    for reason, count in sorted(report.flag_counts.items()):
        print(f"      {reason:<24} {count}")

    print("\n  flagged rows:")
    print(f"  {'row':>4}  {'project_id':<24}  {'reason':<40}  title")
    print("  " + "-" * 96)
    for d in sorted(report.flagged_detail, key=lambda x: x["source_row"]):
        title = (d["title"] or "<none>")[:40]
        print(f"  {d['source_row']:>4}  {d['project_id']:<24}  {d['flag_reason']:<40}  {title}")

    expected = {"duplicate_project_id": 2, "missing_title": 2, "missing_statement": 4}
    print("\n  brief's Section 3 expectation vs actual:")
    ok = True
    for reason, exp in expected.items():
        got = report.flag_counts.get(reason, 0)
        mark = "OK " if got == exp else "!! "
        if got != exp:
            ok = False
        print(f"      {mark}{reason:<24} expected {exp}, got {got}")
    if not ok:
        print(
            "\n  NOTE: a mismatch here is expected if the workbook has been edited since\n"
            "  the brief was written. Inspect the flagged rows above and confirm each is\n"
            "  genuinely dirty - the rule is 'flag, never crash, never drop'."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
