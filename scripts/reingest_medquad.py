import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.bootstrap import bootstrap
bootstrap()

import config
from config.settings import settings
from core.document_manager import DocumentManager
from core.rag_system import RAGSystem


def main():
    print("=== Starting MedQuAD Cloud Re-ingest ===")
    start_time = time.time()

    if not settings.CLOUD_BACKEND_ENABLED:
        print("ERROR: CLOUD_BACKEND_ENABLED must be true in .env to run cloud re-ingest.")
        sys.exit(1)

    medquad_csv = BASE_DIR / "knowledge_base" / "medquad.csv"
    if not medquad_csv.exists():
        print(f"ERROR: {medquad_csv} does not exist.")
        sys.exit(1)

    print(f"Found source CSV: {medquad_csv} ({medquad_csv.stat().st_size / (1024*1024):.2f} MB)")

    # 1. Initialize RAG System
    print("Initializing RAG system (NVIDIA Embeddings + Pinecone + Postgres)...")
    rag = RAGSystem()
    doc_manager = DocumentManager(rag)

    # 2. Clear existing MedQuAD records in Pinecone & Postgres
    source_name = "medquad.csv"
    print(f"Clearing any existing vectors and parent chunks for {source_name}...")
    try:
        doc_manager.delete_document(source_name)
    except Exception as e:
        print(f"Notice during delete: {e}")

    # 3. Ingest MedQuAD dataset
    print(f"Ingesting {source_name} through high-speed cloud pipeline...")

    def progress_callback(fraction, message=""):
        elapsed = time.time() - start_time
        pct = fraction * 100
        print(f"[{elapsed:6.1f}s] {pct:5.1f}% - {message}")

    added, skipped, errors = doc_manager.add_documents(
        [str(medquad_csv)],
        progress_callback=progress_callback,
        uploaded_by="ReingestScript",
        version="1.0",
    )

    elapsed_total = time.time() - start_time
    print("\n=== Re-ingestion Complete ===")
    print(f"Added documents: {added}")
    print(f"Skipped documents: {skipped}")
    print(f"Errors: {errors}")
    print(f"Total time elapsed: {elapsed_total:.2f} seconds ({elapsed_total/60:.2f} minutes)")


if __name__ == "__main__":
    main()
