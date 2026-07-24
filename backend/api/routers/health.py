import asyncio

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    rag_system = request.app.state.rag_system
    graph_ready = bool(rag_system and rag_system.agent_graph)

    database_ok = False
    try:
        from database.supabase_client import connect_prisma, prisma_client

        await connect_prisma()
        await prisma_client.query_raw("SELECT 1")
        database_ok = True
    except Exception:
        pass

    vector_store = None
    if graph_ready:
        try:
            collection = await asyncio.to_thread(
                rag_system.vector_db.get_collection, rag_system.collection_name
            )
            vector_store = type(collection).__name__
        except Exception:
            vector_store = "unavailable"

    return {
        "status": "ok" if graph_ready else "starting",
        "graph_ready": graph_ready,
        "database_ok": database_ok,
        "vector_store": vector_store,
    }


@router.get("/live")
async def live():
    """Process liveness: does not depend on external services."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request):
    """Readiness: graph initialization is mandatory; dependencies are reported explicitly."""
    report = await health(request)
    ready = report["graph_ready"]
    return {**report, "ready": ready}
