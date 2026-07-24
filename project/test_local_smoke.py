import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))


def test_local_storage_imports():
    from db.parent_store_manager import ParentStoreManager
    from db.vector_db_manager import VectorDbManager

    assert ParentStoreManager is not None
    assert VectorDbManager is not None


