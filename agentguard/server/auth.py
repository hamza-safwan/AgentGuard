"""Bearer-token authentication for the v2 ingestion API (BLUEPRINT-7 section 12.9)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from agentguard.storage.models import AuthToken, Project


def hash_token(raw: str) -> str:
    """sha256(raw) - we only ever store hashes, never the plaintext token."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_token(session: Session, project: Project, name: str) -> tuple[AuthToken, str]:
    """Mint a new token, persist its hash, return (row, plaintext)."""
    raw = "ag_" + secrets.token_urlsafe(32)
    row = AuthToken(project_id=project.id, name=name, token_hash=hash_token(raw))
    session.add(row)
    session.flush()
    return row, raw


def verify_token(session: Session, raw: str | None) -> AuthToken:
    """Resolve a bearer token to its DB row or raise HTTP 401 / 403."""
    if not raw:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    row = (
        session.query(AuthToken)
        .filter(AuthToken.token_hash == hash_token(raw))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    if row.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Token revoked.")
    row.last_used_at = datetime.now(UTC)
    return row


def bearer_from_header(authorization: str | None = Header(default=None)) -> str | None:
    """FastAPI Depends-friendly extractor for ``Authorization: Bearer <token>``."""
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()
