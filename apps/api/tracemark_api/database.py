"""SQLAlchemy engine and request-session helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_session_factory: sessionmaker[Session] | None = None


def make_engine(database_url: str) -> Engine:
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **kwargs)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configure_database(engine: Engine) -> sessionmaker[Session]:
    global _session_factory
    _session_factory = make_session_factory(engine)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise RuntimeError("database has not been configured")
    with _session_factory() as session:
        yield session
