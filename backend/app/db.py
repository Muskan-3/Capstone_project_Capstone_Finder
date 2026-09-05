"""SQLAlchemy engine / session wiring.

Defaults to a local SQLite file (zero setup, matches the rest of this
project's "just run it" philosophy). Set ``COMPASS_DATABASE_URL`` to a
``postgresql://`` URL (e.g. a Supabase connection string) to use Postgres in
production - the backend runs as one persistent process (Render, a VM, ...),
so a normal small connection pool is what we want here, same as any other
long-lived Postgres client. Nothing else in the app is Postgres- or
SQLite-specific; SQLAlchemy abstracts the dialect.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs: dict = {"future": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # small, sane pool for a single persistent process talking to Postgres
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 5
    _engine_kwargs["pool_pre_ping"] = True  # survive Supabase idling out a connection

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (register mappers)

    Base.metadata.create_all(bind=engine)
