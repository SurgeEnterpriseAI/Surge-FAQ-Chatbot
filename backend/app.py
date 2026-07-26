from backend.bootstrap import bootstrap

bootstrap()

import asyncio
import os
import threading
import contextlib
import time
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import auth, chat, documents, feedback, health, analytics, analytics_ws, enterprise
from backend.middleware.error_handlers import register_error_handlers
from backend.services.upload_service import UploadService


def _build_rag_system(checkpointer=None):
    from core.document_manager import DocumentManager
    from core.rag_system import RAGSystem

    rag_system = RAGSystem()
    rag_system.initialize(checkpointer=checkpointer)
    return rag_system, DocumentManager(rag_system)


def create_app(init_resources: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if init_resources:
            from database.supabase_client import connect_prisma, disconnect_prisma
            from backend.services.metrics_collector import metrics_collector

            try:
                await connect_prisma()
            except Exception as e:
                print(f"WARNING: Prisma connection failed at startup: {e}")
            
            metrics_collector.start()

            # Opened here, not inside _build_rag_system: an AsyncConnectionPool
            # binds to the loop that opens it, and the RAG system is built in a
            # worker thread that has no running loop.
            from rag_agent.graph import open_postgres_checkpointer

            checkpointer, app.state.checkpointer_pool = await open_postgres_checkpointer()

            try:
                app.state.rag_system, app.state.doc_manager = await asyncio.to_thread(
                    _build_rag_system, checkpointer
                )
            except Exception as e:
                print(f"WARNING: RAG system initialization failed: {e}")
                print("Server starting in degraded mode — chat and document upload will return 503 until the issue is resolved.")
        yield
        if init_resources:
            from backend.services.metrics_collector import metrics_collector
            metrics_collector.stop()
            try:
                app.state.rag_system.observability.flush()
            except Exception:
                pass
            if app.state.checkpointer_pool is not None:
                try:
                    await app.state.checkpointer_pool.close()
                except Exception:
                    pass
            try:
                await asyncio.wait_for(disconnect_prisma(), timeout=int(os.environ.get("GRACEFUL_SHUTDOWN_SECONDS", "20")))
            except Exception:
                pass

    app = FastAPI(title="Agentic RAG API", version="1.0.0", lifespan=lifespan)
    app.state.rag_system = None
    app.state.doc_manager = None
    app.state.checkpointer_pool = None
    app.state.ingest_lock = threading.Lock()
    app.state.upload_service = UploadService()

    @app.middleware("http")
    async def record_request_latency(request, call_next):
        """Feed real request durations to the metrics collector.

        Must always return a Response — if call_next itself raises (e.g. the
        Starlette streaming handshake fails mid-request) we return a 500 JSON
        instead of propagating the exception, which would cause Starlette to
        panic with 'No response returned.'.
        """
        from backend.services.metrics_collector import latency_tracker

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            latency_tracker.record("api", (time.perf_counter() - started) * 1000)
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {exc}"},
            )
        latency_tracker.record("api", (time.perf_counter() - started) * 1000)
        return response

    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(feedback.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(enterprise.router, prefix="/api")
    app.include_router(analytics_ws.router)
    return app


app = create_app()
