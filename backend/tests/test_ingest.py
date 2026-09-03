"""Section 3 / Definition-of-Done: ingestion flags the known-dirty rows and never crashes."""

from __future__ import annotations

import pytest

from app.config import settings
from app.ml.ingest import clean, ingest_file, read_source


@pytest.fixture(scope="module")
def cleaned():
    sheet, raw = read_source(settings.source_workbook)
    rows, report = clean(raw, source="test", sheet=sheet, source_batch="initial")
    return rows, report


def test_all_200_rows_kept(cleaned):
    rows, report = cleaned
    assert report.total_rows == 200
    assert len(rows) == 200  # nothing dropped, ever


def test_duplicate_project_id_suffixed_and_flagged(cleaned):
    rows, _ = cleaned
    dupes = [r for r in rows if r.original_project_id == "ASAC-CAP-PROJ-562"]
    assert len(dupes) == 1
    assert dupes[0].project_id == "ASAC-CAP-PROJ-562-B"
    both = [r for r in rows if (r.project_id or "").startswith("ASAC-CAP-PROJ-562")]
    assert len(both) == 2
    assert all(r.is_flagged and "duplicate_project_id" in r.flag_reason for r in both)


def test_missing_titles_flagged_not_dropped(cleaned):
    rows, report = cleaned
    missing_title = [r for r in rows if r.flag_reason and "missing_title" in r.flag_reason]
    # brief said 2; the workbook has since gained rows titled "v" and "uu"
    assert len(missing_title) >= 2
    assert all(r.is_flagged for r in missing_title)


def test_missing_statements_flagged_not_dropped(cleaned):
    rows, _ = cleaned
    missing_stmt = [r for r in rows if r.flag_reason and "missing_statement" in r.flag_reason]
    assert len(missing_stmt) >= 4  # brief said 4; real file has more
    # the two literal-number statements from the brief
    numeric_rows = {r.project_id for r in missing_stmt}
    assert {"ASAC-CAP-PROJ-507", "ASAC-CAP-PROJ-670"} <= numeric_rows


def test_flagged_rows_have_a_reason(cleaned):
    rows, _ = cleaned
    for r in rows:
        assert r.is_flagged == (r.flag_reason is not None)


def test_csv_batch_ingest():
    csv = (
        "ProjectID,Title,Problem Statement\n"
        "B-1,Good One,\"A sufficiently long and specific problem statement about edge ML.\"\n"
        "B-2,,\"no title here but a real statement of adequate length for the pool\"\n"
        "B-3,Bad Statement,7\n"
    )
    rows, report = ingest_file(csv.encode(), "batch.csv", source_batch="t")
    assert len(rows) == 3
    assert report.flagged_rows == 2
    assert {r.project_id: r.is_flagged for r in rows} == {"B-1": False, "B-2": True, "B-3": True}
