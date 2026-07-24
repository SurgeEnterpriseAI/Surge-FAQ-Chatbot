"""Runtime verification script for Python release and cloud services (Pinecone, Supabase, NVIDIA)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "project"))

MINIMUM_PYTHON = (3, 11)


def check_python() -> bool:
    version = sys.version_info[:2]
    if MINIMUM_PYTHON <= version:
        print(f"[OK] Python {sys.version.split()[0]} is supported.")
        return True
    print(f"[FAIL] Unsupported Python version {sys.version.split()[0]}. Need >= 3.11")
    return False


def check_env() -> bool:
    from config.settings import settings

    missing = []
    if not settings.PINECONE_API_KEY:
        missing.append("PINECONE_API_KEY")
    if not settings.DATABASE_URL:
        missing.append("DATABASE_URL")
    if not settings.NVIDIA_API_KEY:
        missing.append("NVIDIA_API_KEY")

    if missing:
        print(f"[FAIL] Missing environment variables: {', '.join(missing)}")
        return False
    print("[OK] Core environment variables present.")
    return True


def check_pinecone() -> bool:
    try:
        from config.settings import settings
        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        indexes = [idx.name for idx in pc.list_indexes()]
        print(f"[OK] Connected to Pinecone. Found indexes: {indexes}")
        return True
    except Exception as e:
        print(f"[FAIL] Pinecone connection error: {e}")
        return False


def check_nvidia_embeddings() -> bool:
    try:
        from embeddings.embedding_service import NvidiaEmbeddings

        embedder = NvidiaEmbeddings()
        vec = embedder.embed_query("test runtime connection")
        if len(vec) == 1024:
            print(f"[OK] Connected to NVIDIA Embeddings API. Vector dimension: {len(vec)}")
            return True
        else:
            print(f"[FAIL] Unexpected NVIDIA embedding dimension: {len(vec)} (expected 1024)")
            return False
    except Exception as e:
        print(f"[FAIL] NVIDIA Embeddings error: {e}")
        return False


def main() -> int:
    print("=== Agentic-RAG Runtime Verification ===")
    ok_python = check_python()
    ok_env = check_env()
    ok_pinecone = check_pinecone() if ok_env else False
    ok_nvidia = check_nvidia_embeddings() if ok_env else False

    if ok_python and ok_env and ok_pinecone and ok_nvidia:
        print("\nAll runtime checks passed successfully!")
        return 0
    else:
        print("\nRuntime checks completed with warnings or failures.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
