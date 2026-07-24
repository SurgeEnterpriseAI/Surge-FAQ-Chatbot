import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "project"))

from config.settings import settings
import psycopg2

def apply_migration():
    db_url = settings.DATABASE_URL
    if not db_url:
        print("DATABASE_URL is missing!")
        return

    # Extract connection parameters or pass URI directly
    print(f"Connecting to database to apply migration...")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    sql_file = BASE_DIR / "project" / "migrations" / "002_add_documents_table.sql"
    sql = sql_file.read_text(encoding="utf-8")

    print(f"Executing SQL migration from {sql_file.name}...")
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    print("Migration 002_add_documents_table.sql executed successfully!")

if __name__ == "__main__":
    apply_migration()
