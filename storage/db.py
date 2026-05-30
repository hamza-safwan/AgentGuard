"""SQLAlchemy database setup."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/agentguard"


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine(url: str | None = None):
    db_url = url or database_url()
    kwargs = {"future": True}
    if db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(db_url, **kwargs)


def get_session(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(url), autoflush=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(url: str | None = None) -> Generator[Session, None, None]:
    SessionLocal = get_session(url)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(url: str | None = None) -> None:
    from agentguard.storage import models  # noqa: F401

    Base.metadata.create_all(get_engine(url))
