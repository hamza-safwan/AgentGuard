"""``/api/v2/tokens/*`` - issue and revoke ingestion tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agentguard.server.auth import issue_token
from agentguard.server.dependencies import db_session
from agentguard.storage.models import AuthToken, Project

router = APIRouter(prefix="/api/v2/tokens", tags=["observability"])


class TokenCreate(BaseModel):
    project_id: str
    name: str


@router.get("")
def list_tokens(
    project_id: str | None = None,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    q = session.query(AuthToken)
    if project_id:
        q = q.filter(AuthToken.project_id == project_id)
    return {
        "tokens": [
            {
                "id": t.id,
                "project_id": t.project_id,
                "name": t.name,
                "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
                "created_at": t.created_at.isoformat(),
                "revoked_at": t.revoked_at.isoformat() if t.revoked_at else None,
            }
            for t in q.order_by(AuthToken.created_at.desc()).all()
        ]
    }


@router.post("", status_code=201)
def create_token(
    payload: TokenCreate,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    project = session.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    row, raw = issue_token(session, project, payload.name)
    session.commit()
    # The plaintext token is returned ONCE; the server only ever stores its hash.
    return {
        "id": row.id,
        "name": row.name,
        "token": raw,
        "warning": "Store this token now; it cannot be retrieved later.",
    }


@router.post("/{token_id}/revoke", status_code=200)
def revoke_token(token_id: str, session: Session = Depends(db_session)) -> dict[str, Any]:
    row = session.get(AuthToken, token_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Token not found.")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        session.commit()
    return {"id": row.id, "revoked_at": row.revoked_at.isoformat()}
