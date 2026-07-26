"""Runtime bootstrap shared by every backend entrypoint (server and tests).

Must run before any module under project/ is imported: sets the Windows
selector event loop policy required by the async psycopg pool behind the
LangGraph Postgres checkpointer, puts project/ on sys.path (its modules use
bare imports like `import config`), and loads project/.env.
"""
import asyncio
import sys
import warnings
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent / "project"

_bootstrapped = False


def selector_event_loop() -> asyncio.AbstractEventLoop:
    """Event loop factory for uvicorn (passed as ``loop=`` from backend.main).

    psycopg's async mode refuses to run on Windows' ProactorEventLoop, which is
    exactly what uvicorn's own factory hardcodes there (uvicorn/loops/asyncio.py).
    Setting the event loop policy does not help: uvicorn hands a loop_factory to
    asyncio.Runner, which bypasses the policy completely. Supplying this factory
    instead is what keeps the Postgres checkpointer usable on Windows.
    """
    return asyncio.SelectorEventLoop()


def bootstrap() -> None:
    global _bootstrapped
    if _bootstrapped:
        return

    if sys.platform == "win32":
        # Only reaches entry points that build their own loop via
        # asyncio.new_event_loop() — the uvicorn server loop comes from
        # selector_event_loop above. Both policy APIs are deprecated in 3.14
        # and removed in 3.16, so this is best-effort.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except AttributeError:
                pass

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    project_path = str(PROJECT_DIR)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env", override=True)

    _bootstrapped = True
