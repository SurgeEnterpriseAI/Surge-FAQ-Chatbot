from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import require_admin
from database.supabase_client import connect_prisma, prisma_client

router = APIRouter(prefix="/enterprise", tags=["enterprise"])

# Telemetry is an optional enhancement.  It must never make the admin UI wait
# for the database driver's (currently 60-second) connection timeout.
_TELEMETRY_TIMEOUT_SECONDS = 2


async def _find_agent_logs(*, where: dict | None = None, take: int | None = None, order: dict | None = None):
    """Return no traces when optional telemetry storage is unavailable."""
    try:
        await asyncio.wait_for(connect_prisma(), timeout=_TELEMETRY_TIMEOUT_SECONDS)
        if not prisma_client.is_connected():
            return []
        return await asyncio.wait_for(
            prisma_client.agentlog.find_many(where=where, take=take, order=order),
            timeout=_TELEMETRY_TIMEOUT_SECONDS,
        )
    except Exception:
        return []


def _json(value: Any) -> Any:
    if isinstance(value, str):
        import json
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


@router.get("/traces")
async def list_traces(limit: int = 50, _admin: dict = Depends(require_admin)):
    logs = await _find_agent_logs(order={"timestamp": "desc"}, take=min(max(limit, 1), 200))
    return [{"id": log.id, "thread_id": log.threadId, "node": log.nodeName, "event": log.eventType,
             "timestamp": log.timestamp, "payload": _json(log.payload)} for log in logs]


@router.get("/traces/{thread_id}")
async def trace_detail(thread_id: str, _admin: dict = Depends(require_admin)):
    logs = await _find_agent_logs(where={"threadId": thread_id}, order={"timestamp": "asc"})
    if not logs:
        raise HTTPException(status_code=404, detail="Trace not found")
    # Replay is presentation-only: it returns immutable recorded events and never re-executes a graph.
    return {"thread_id": thread_id, "replay_mode": "visualization", "events": [
        {"node": log.nodeName, "event": log.eventType, "timestamp": log.timestamp, "payload": _json(log.payload)}
        for log in logs
    ]}


@router.get("/prompts")
async def list_prompts(_admin: dict = Depends(require_admin)):
    await connect_prisma()
    try:
        rows = await prisma_client.promptversion.find_many(order={"createdAt": "desc"})
    except Exception:
        return {"items": [], "migration_required": True}
    return {"items": [{"id": r.id, "key": r.key, "version": r.version, "active": r.active,
                        "content": r.content, "metadata": _json(r.metadata)} for r in rows]}


@router.post("/prompts")
async def create_prompt(body: dict, _admin: dict = Depends(require_admin)):
    key, content = str(body.get("key", "")).strip(), str(body.get("content", "")).strip()
    if not key or not content:
        raise HTTPException(status_code=422, detail="key and content are required")
    await connect_prisma()
    previous = await prisma_client.promptversion.find_many(where={"key": key}, order={"version": "desc"}, take=1)
    version = (previous[0].version if previous else 0) + 1
    created = await prisma_client.promptversion.create(data={"id": str(uuid.uuid4()), "key": key, "version": version,
        "content": content, "active": bool(body.get("active", False)), "metadata": body.get("metadata")})
    return {"id": created.id, "key": key, "version": version}


@router.get("/costs")
async def costs(_admin: dict = Depends(require_admin)):
    await connect_prisma()
    try:
        rows = await prisma_client.costusage.find_many(order={"createdAt": "desc"}, take=500)
    except Exception:
        return {"total_usd": 0, "items": [], "migration_required": True}
    return {"total_usd": sum(row.costUsd for row in rows), "items": [
        {"trace_id": row.traceId, "agent": row.agentName, "model": row.model, "cost_usd": row.costUsd,
         "input_tokens": row.inputTokens, "output_tokens": row.outputTokens, "created_at": row.createdAt} for row in rows
    ]}
