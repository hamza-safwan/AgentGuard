"""``/api/v2/traces/ingest`` - observability ingestion endpoint.

Accepts batched, optionally gzipped trace payloads from the SDK transport.
Each batch is enqueued onto a Dramatiq queue (or processed inline when no
broker is configured) so the HTTP request returns immediately.
"""

from __future__ import annotations

import gzip
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from agentguard.schemas.trace import AgentTrace
from agentguard.server.auth import bearer_from_header, verify_token
from agentguard.server.dependencies import db_session

router = APIRouter(prefix="/api/v2/traces", tags=["observability"])

MAX_BATCH_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/ingest")
async def ingest_traces(
    request: Request,
    session: Session = Depends(db_session),
    authorization: str | None = Header(default=None),
    content_encoding: str | None = Header(default=None),
) -> dict[str, Any]:
    raw = bearer_from_header(authorization)
    token = verify_token(session, raw)
    session.commit()  # persist last_used_at

    body = await request.body()
    if len(body) > MAX_BATCH_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large.")
    if (content_encoding or "").lower() == "gzip":
        try:
            body = gzip.decompress(body)
        except OSError as exc:
            raise HTTPException(status_code=400, detail=f"Bad gzip body: {exc}") from exc

    import json

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, dict) or "traces" not in payload:
        raise HTTPException(status_code=400, detail="Body must be {'traces': [...]}.")

    accepted: list[str] = []
    rejected: list[dict[str, str]] = []
    for entry in payload.get("traces", []):
        try:
            trace = AgentTrace(**entry)
        except Exception as exc:
            rejected.append({"reason": str(exc)[:200]})
            continue
        try:
            from agentguard.jobs.ingest_worker import enqueue_trace

            enqueue_trace(trace, project_id=token.project_id)
            accepted.append(trace.trace_id)
        except Exception as exc:
            rejected.append({"trace_id": trace.trace_id, "reason": str(exc)[:200]})

    return {
        "ingested": len(accepted),
        "rejected": len(rejected),
        "errors": rejected[:20],
        "received_at": datetime.now(UTC).isoformat(),
    }
