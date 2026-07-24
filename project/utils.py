import os
import shutil
import config
import pymupdf.layout
import pymupdf4llm
from pathlib import Path
import glob
import tiktoken
from functools import lru_cache


def clear_directory_contents(directory: Path) -> None:
    """Delete everything under directory but not the directory itself (safe for Docker volume / bind mount roots)."""
    directory = Path(directory)
    if not directory.is_dir():
        return
    for child in directory.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


os.environ["TOKENIZERS_PARALLELISM"] = "false"

def pdf_to_markdown(pdf_path, output_dir):
    doc = pymupdf.open(pdf_path)
    md = pymupdf4llm.to_markdown(doc, header=False, footer=False, page_separators=True, ignore_images=True, write_images=False, image_path=None)
    md_cleaned = md.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='ignore')
    output_path = Path(output_dir) / Path(pdf_path).stem
    Path(output_path).with_suffix(".md").write_bytes(md_cleaned.encode('utf-8'))

def pdfs_to_markdowns(path_pattern, overwrite: bool = False):
    output_dir = Path(config.MARKDOWN_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    single_path = Path(path_pattern)
    if single_path.is_file():
        pdf_paths = [single_path]
    else:
        pdf_paths = map(Path, glob.glob(path_pattern))

    for pdf_path in pdf_paths:
        md_path = (output_dir / pdf_path.stem).with_suffix(".md")
        if overwrite or not md_path.exists():
            pdf_to_markdown(pdf_path, output_dir)

@lru_cache(maxsize=1)
def _get_token_encoding():
    try:
        return tiktoken.encoding_for_model("gpt-4")
    except Exception:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None


def estimate_context_tokens(messages: list) -> int:
    contents = [
        str(msg.content)
        for msg in messages
        if hasattr(msg, "content") and msg.content
    ]
    encoding = _get_token_encoding()
    if encoding is None:
        return sum(max(1, len(content) // 4) for content in contents)
    return sum(len(encoding.encode(content)) for content in contents)


def ingest_knowledge_base(doc_manager) -> None:
    """
    Auto-ingest all PDFs and Markdown files found in KNOWLEDGE_BASE_DIR.
    Skips files already indexed. Safe to call on every startup.
    """
    kb_dir = Path(config.KNOWLEDGE_BASE_DIR)
    if not kb_dir.exists():
        print(f"⚠️  knowledge_base/ folder not found at {kb_dir}. Skipping auto-ingestion.")
        return

    allowed_extensions = (".pdf", ".docx", ".pptx", ".txt", ".md", ".csv", ".xlsx", ".xls")
    supported = [p for p in kb_dir.iterdir() if p.suffix.lower() in allowed_extensions]
    if not supported:
        print("⚠️  No supported files found in knowledge_base/. Skipping auto-ingestion.")
        return

    print(f"\n📚 Auto-ingesting {len(supported)} document(s) from knowledge_base/ ...")
    added, skipped, errors = doc_manager.add_documents([str(p) for p in supported])
    print(f"   ✅ Added: {added} | ⏭️  Already indexed: {skipped}")
    for message in errors:
        print(f"   ❌ {message}")

