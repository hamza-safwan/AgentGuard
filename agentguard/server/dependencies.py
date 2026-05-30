"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from agentguard.storage.db import get_session


def db_session() -> Generator[Session, None, None]:
    SessionLocal = get_session()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
