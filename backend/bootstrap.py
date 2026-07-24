"""Runtime bootstrap shared by every backend entrypoint (server and tests).

Must run before any module under project/ is imported: sets the Windows
selector event loop policy required by the async psycopg pool behind the
LangGraph Postgres checkpointer, puts project/ on sys.path (its modules use
bare imports like `import config`), and loads project/.env.
"""
import asyncio
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent / "project"

_bootstrapped = False


def bootstrap() -> None:
    global _bootstrapped
    if _bootstrapped:
        return

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    project_path = str(PROJECT_DIR)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env", override=True)

    _bootstrapped = True
