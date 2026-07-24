import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(asyncio.TimeoutError)
    async def timeout_handler(request: Request, exc: asyncio.TimeoutError):
        return JSONResponse(
            status_code=504,
            content={"detail": "The request timed out. Please try again."},
        )

    @app.exception_handler(ConnectionError)
    async def connection_handler(request: Request, exc: ConnectionError):
        return JSONResponse(
            status_code=503,
            content={"detail": "A backing service (database or vector store) is unavailable. Please try again later."},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected server error occurred."},
        )
