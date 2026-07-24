import csv
from pathlib import Path
import pytest
from project.loaders.medquad_loader import load_medquad, MAX_CHILD_TEXT_LEN

def test_medquad_loader_basic(tmp_path: Path):
    csv_file = tmp_path / "test_medquad.csv"
    records = [
        {
            "question": "What is Glaucoma?",
            "answer": "Glaucoma is an eye condition causing vision loss.",
            "source": "NIHSeniorHealth",
            "focus_area": "Glaucoma",
            "question_type": "Definition"
        },
        {
            "question": "What are symptoms of High Blood Pressure?",
            "answer": "High blood pressure often has no symptoms.",
            "source": "NIHSeniorHealth",
            "focus_area": "High Blood Pressure",
            "question_type": "Symptoms"
        }
    ]

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "answer", "source", "focus_area", "question_type"])
        writer.writeheader()
        writer.writerows(records)

    parents, children = load_medquad(csv_file, doc_id="test_medquad", source_name="test_medquad.csv")

    assert len(parents) == 2
    assert len(children) == 2

    parent_id_0, parent_doc_0 = parents[0]
    child_doc_0 = children[0]

    assert parent_id_0 == "test_medquad_p0"
    assert "What is Glaucoma?" in child_doc_0.page_content
    assert "Focus: Glaucoma" in child_doc_0.page_content
    assert "Answer: Glaucoma is an eye condition" in parent_doc_0.page_content
    assert child_doc_0.metadata["source"] == "test_medquad.csv"

def test_medquad_loader_edge_cases(tmp_path: Path):
    csv_file = tmp_path / "edge_cases.csv"
    records = [
        # Missing question -> skipped
        {
            "question": "",
            "answer": "Answer with no question",
            "focus_area": "",
            "question_type": ""
        },
        # Missing answer -> fallback answer string
        {
            "question": "What is Diabetes?",
            "answer": "",
            "focus_area": "Diabetes",
            "question_type": ""
        },
        # Extremely long question/focus -> truncated child text
        {
            "question": "Q" * 3000,
            "answer": "Long answer text",
            "focus_area": "Long Focus",
            "question_type": ""
        }
    ]

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "answer", "source", "focus_area", "question_type"])
        writer.writeheader()
        writer.writerows(records)

    parents, children = load_medquad(csv_file, doc_id="edge_cases", source_name="edge_cases.csv")

    # Only 2 rows processed (row 0 skipped due to missing question)
    assert len(parents) == 2
    assert len(children) == 2

    # Check missing answer fallback
    _, parent_doc_1 = parents[0]
    assert "Answer: Information not provided." in parent_doc_1.page_content

    # Check child chunk text truncation limit
    child_doc_long = children[1]
    assert len(child_doc_long.page_content) <= MAX_CHILD_TEXT_LEN
