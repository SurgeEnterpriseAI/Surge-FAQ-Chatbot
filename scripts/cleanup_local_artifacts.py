import argparse
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TARGET_DIRS = [
    BASE_DIR / "parent_store",
    BASE_DIR / "markdown_docs",
    BASE_DIR / "archived_markdown",
    BASE_DIR / "project" / "uploads",
    BASE_DIR / "qdrant_db",
]


def get_dir_stats(path: Path) -> tuple[int, int]:
    """Returns (file_count, total_bytes) recursively."""
    if not path.exists():
        return 0, 0
    file_count = 0
    total_bytes = 0
    for p in path.rglob("*"):
        if p.is_file():
            file_count += 1
            total_bytes += p.stat().st_size
    return file_count, total_bytes


def main():
    parser = argparse.ArgumentParser(
        description="Clean up legacy local artifact directories."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Perform actual deletion. Default is dry-run mode.",
    )
    args = parser.parse_args()

    is_dry_run = not args.yes

    print("=== Local Artifact Cleanup Tool ===")
    if is_dry_run:
        print("[DRY-RUN MODE] No files will be deleted. Pass --yes to delete.\n")
    else:
        print("[DELETION MODE] Preparing to delete local artifact directories...\n")

    total_files_found = 0
    total_bytes_found = 0

    for dir_path in TARGET_DIRS:
        count, size = get_dir_stats(dir_path)
        total_files_found += count
        total_bytes_found += size
        mb_size = size / (1024 * 1024)

        if dir_path.exists():
            print(f"Directory: {dir_path.relative_to(BASE_DIR)}")
            print(f"  Files: {count:,}")
            print(f"  Size:  {mb_size:.2f} MB")

            if not is_dry_run:
                try:
                    shutil.rmtree(dir_path)
                    print("  Status: DELETED\n")
                except Exception as e:
                    print(f"  Status: ERROR ({e})\n")
            else:
                print("  Action: WOULD DELETE\n")
        else:
            print(f"Directory: {dir_path.relative_to(BASE_DIR)} (Does not exist)\n")

    total_mb = total_bytes_found / (1024 * 1024)
    print("=== Summary ===")
    print(f"Total files found: {total_files_found:,}")
    print(f"Total space reclamation: {total_mb:.2f} MB")

    if is_dry_run and total_files_found > 0:
        print("\nTo delete these directories, run:")
        print("  python scripts/cleanup_local_artifacts.py --yes")


if __name__ == "__main__":
    main()
