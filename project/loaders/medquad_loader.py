import csv
from pathlib import Path
from typing import List, Optional, Tuple
from langchain_core.documents import Document

MAX_CHILD_TEXT_LEN = 1500


def load_medquad(
    csv_path: Path,
    doc_id: str = None,
    source_name: Optional[str] = None,
    document_id: Optional[str] = None,
) -> Tuple[List[Tuple[str, Document]], List[Document]]:
    """Each Q/A row = 1 parent = 1 child. No recursive splitting.

    - Child chunk text: Question + Focus Area (optimized for vector similarity search)
    - Parent chunk content: Question + Answer + Focus Area + Type (full Q&A context)
    """
    parents: List[Tuple[str, Document]] = []
    children: List[Document] = []
    actual_source_name = source_name or csv_path.name

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            question = (row.get("question") or "").strip()
            answer = (row.get("answer") or "").strip()
            focus_area = (row.get("focus_area") or "").strip()
            question_type = (row.get("question_type") or "").strip()

            if not question:
                continue

            if not answer:
                answer = "Information not provided."

            # Child chunk embeds question + focus area for optimal query alignment
            child_text = f"Question: {question}"
            if focus_area:
                child_text += f"\nFocus: {focus_area}"

            # Truncate child text safely to fit model context limit (~512 tokens / ~1500 chars)
            if len(child_text) > MAX_CHILD_TEXT_LEN:
                child_text = child_text[:MAX_CHILD_TEXT_LEN]

            # Full parent content for answer generation
            parent_text = f"Question: {question}\nAnswer: {answer}"
            if focus_area:
                parent_text += f"\nFocus: {focus_area}"
            if question_type:
                parent_text += f"\nType: {question_type}"

            parent_id = f"{Path(actual_source_name).stem}_p{i}"

            metadata = {
                "source": actual_source_name,
                "focus_area": focus_area,
                "question_type": question_type,
                "row": i,
                "parent_id": parent_id,
            }
            if document_id:
                metadata["document_id"] = document_id

            parent_doc = Document(page_content=parent_text, metadata=dict(metadata))

            child_metadata = dict(metadata)
            child_metadata["id"] = f"{parent_id}_c0"
            child_doc = Document(page_content=child_text, metadata=child_metadata)

            parents.append((parent_id, parent_doc))
            children.append(child_doc)

    return parents, children
