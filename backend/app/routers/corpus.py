from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..ml.ingest import MIN_STATEMENT_CHARS, ingest_file
from ..models import ProblemStatement
from ..schemas import CorpusPage, ProblemStatementOut, ProblemStatementPatch, UploadReport
from ..training import get_active_artifacts

router = APIRouter(prefix="/api/corpus", tags=["corpus"])


def _decorate(item: ProblemStatement, labels: dict[int, str]) -> ProblemStatementOut:
    out = ProblemStatementOut.model_validate(item)
    if item.cluster_id is not None:
        out.cluster_label = labels.get(item.cluster_id)
    return out


def _cluster_labels(db: Session) -> dict[int, str]:
    art = get_active_artifacts(db)
    if not art:
        return {}
    return {cid: art.cluster_label(cid) for cid in art.cluster_sizes}


@router.get("", response_model=CorpusPage)
def list_corpus(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: str | None = None,
    cluster_id: int | None = None,
    flagged: bool | None = None,
) -> CorpusPage:
    stmt = select(ProblemStatement)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                ProblemStatement.title.ilike(like),
                ProblemStatement.statement.ilike(like),
                ProblemStatement.project_id.ilike(like),
            )
        )
    if cluster_id is not None:
        stmt = stmt.where(ProblemStatement.cluster_id == cluster_id)
    if flagged is not None:
        stmt = stmt.where(ProblemStatement.is_flagged.is_(flagged))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ProblemStatement.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    labels = _cluster_labels(db)
    return CorpusPage(
        items=[_decorate(r, labels) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/flagged", response_model=list[ProblemStatementOut])
def list_flagged(db: Session = Depends(get_db)) -> list[ProblemStatementOut]:
    rows = db.scalars(
        select(ProblemStatement)
        .where(ProblemStatement.is_flagged.is_(True))
        .order_by(ProblemStatement.id)
    ).all()
    labels = _cluster_labels(db)
    return [_decorate(r, labels) for r in rows]


@router.patch("/{item_id}", response_model=ProblemStatementOut)
def fix_flagged(
    item_id: int, patch: ProblemStatementPatch, db: Session = Depends(get_db)
) -> ProblemStatementOut:
    item = db.get(ProblemStatement, item_id)
    if item is None:
        raise HTTPException(404, f"problem statement {item_id} not found")

    if patch.project_id is not None:
        item.project_id = patch.project_id.strip()
    if patch.title is not None:
        item.title = patch.title.strip() or None
    if patch.statement is not None:
        item.statement = patch.statement.strip() or None

    if patch.clear_flag:
        problems = []
        if not item.title:
            problems.append("missing_title")
        if not item.statement or len(item.statement) < MIN_STATEMENT_CHARS:
            problems.append("missing_statement")
        # a resolved duplicate keeps its suffixed id but is no longer "dirty"
        dupes = db.scalars(
            select(ProblemStatement).where(
                ProblemStatement.project_id == item.project_id,
                ProblemStatement.id != item.id,
            )
        ).all()
        if dupes:
            problems.append("duplicate_project_id")
        item.flag_reason = "; ".join(problems) or None
        item.is_flagged = bool(problems)

    db.commit()
    db.refresh(item)
    return _decorate(item, _cluster_labels(db))


@router.post("/upload", response_model=UploadReport)
async def upload_batch(
    file: UploadFile = File(...),
    source_batch: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> UploadReport:
    data = await file.read()
    batch = (source_batch or file.filename or "batch").rsplit(".", 1)[0]
    # avoid colliding batch tags
    existing = {
        b for (b,) in db.execute(select(ProblemStatement.source_batch).distinct()).all()
    }
    tag, n = batch, 2
    while tag in existing:
        tag = f"{batch}-{n}"
        n += 1

    try:
        rows, report = ingest_file(data, file.filename or "batch.xlsx", source_batch=tag)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    known = {p for (p,) in db.execute(select(ProblemStatement.project_id)).all()}
    inserted = 0
    for r in rows:
        pid = r.project_id
        if pid in known:  # de-dupe against what's already stored
            suffix = 2
            while f"{pid}-b{suffix}" in known:
                suffix += 1
            pid = f"{pid}-b{suffix}"
        known.add(pid)
        db.add(
            ProblemStatement(
                project_id=pid,
                title=r.title,
                statement=r.statement,
                is_flagged=r.is_flagged,
                flag_reason=r.flag_reason,
                source_batch=tag,
                original_project_id=r.original_project_id or (r.project_id if pid != r.project_id else None),
            )
        )
        inserted += 1
    db.commit()

    return UploadReport(source_batch=tag, report=report.as_dict(), inserted=inserted)
