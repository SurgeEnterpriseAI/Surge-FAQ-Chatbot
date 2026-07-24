import pytest
from pathlib import Path
from project.loaders.medquad_loader import load_medquad

def test_medquad_retrieval_topics(tmp_path: Path):
    """Test chunk generation and topic representation for multi-topic MedQuad dataset."""
    sample_csv = tmp_path / "medquad_sample.csv"
    import csv

    sample_rows = [
        {"question": "What is Glaucoma?", "answer": "Glaucoma is eye pressure build up.", "source": "NIH", "focus_area": "Glaucoma", "question_type": "Definition"},
        {"question": "What causes High Blood Pressure?", "answer": "Kidney salt imbalances and lifestyle.", "source": "NIH", "focus_area": "High Blood Pressure", "question_type": "Causes"},
        {"question": "What are symptoms of Diabetes?", "answer": "Frequent urination and excessive thirst.", "source": "NIH", "focus_area": "Diabetes", "question_type": "Symptoms"},
        {"question": "How to treat Cataracts?", "answer": "Surgery to replace cloudy lens.", "source": "NIH", "focus_area": "Cataracts", "question_type": "Treatment"},
        {"question": "What triggers Asthma?", "answer": "Dust mites, pollen, cold air.", "source": "NIH", "focus_area": "Asthma", "question_type": "Triggers"}
    ]

    with open(sample_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "answer", "source", "focus_area", "question_type"])
        writer.writeheader()
        writer.writerows(sample_rows)

    parents, children = load_medquad(sample_csv, doc_id="medquad_sample", source_name="medquad_sample.csv")

    assert len(parents) == 5
    assert len(children) == 5

    topics = ["Glaucoma", "High Blood Pressure", "Diabetes", "Cataracts", "Asthma"]
    for i, topic in enumerate(topics):
        child_text = children[i].page_content
        parent_text = parents[i][1].page_content

        assert topic in child_text
        assert topic in parent_text
        assert "Answer:" in parent_text
