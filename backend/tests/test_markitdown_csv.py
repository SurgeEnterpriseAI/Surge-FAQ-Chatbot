import tempfile
from pathlib import Path

import pytest

from document_processing.markitdown_processor import DocumentProcessor

def test_csv_processor_unicode_decode():
    processor = DocumentProcessor()

    # CSV content with > 4096 bytes of pure ASCII first, then non-ASCII characters to trigger sniff error in MarkItDown
    header = "question,answer\n"
    padding = "a,b\n" * 1500
    non_ascii_line = "Is this a smart quote?,Yes it’s a smart quote.\nAccented?,élégant\n"
    csv_content = header + padding + non_ascii_line

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="wb", delete=False) as tmp:
        tmp.write(csv_content.encode("utf-8"))
        tmp_path = Path(tmp.name)

    try:
        markdown_result = processor.process_document(tmp_path)
        assert markdown_result is not None
        assert "Yes it’s a smart quote." in markdown_result
        assert "élégant" in markdown_result
        assert "- **question**: Is this a smart quote?" in markdown_result
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _write_workbook(sheets: dict) -> Path:
    """Write {sheet_name: [rows]} to a temporary .xlsx and return its path."""
    openpyxl = pytest.importorskip("openpyxl")

    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for sheet_name, rows in sheets.items():
        worksheet = workbook.create_sheet(title=sheet_name)
        for row in rows:
            worksheet.append(row)

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    workbook.save(tmp_path)
    return tmp_path


def test_xlsx_converts_to_records_not_pipe_table():
    """Spreadsheet rows must survive chunking, so each row is its own record."""
    processor = DocumentProcessor()
    tmp_path = _write_workbook(
        {
            "FAQ": [
                ["Question", "Answer", "Category"],
                ["What is the refund window?", "30 days from delivery.", "Returns"],
                ["How long is shipping?", "3-5 business days.", "Shipping"],
                ["", "", ""],
            ]
        }
    )

    try:
        markdown_result = processor.process_document(tmp_path)

        # Single sheet: no sheet prefix, matching the CSV output shape.
        assert "## Record 1" in markdown_result
        assert "## Record 2" in markdown_result
        assert "- **Question**: How long is shipping?" in markdown_result
        assert "- **Answer**: 3-5 business days." in markdown_result
        # The blank row must not produce an empty record.
        assert "## Record 3" not in markdown_result
        # No raw pipe table survives.
        assert "| --- |" not in markdown_result
    finally:
        tmp_path.unlink(missing_ok=True)


def test_xlsx_multi_sheet_labels_records_by_sheet():
    processor = DocumentProcessor()
    tmp_path = _write_workbook(
        {
            "Billing": [["Topic", "Detail"], ["Invoices", "Issued monthly."]],
            "Shipping": [["Topic", "Detail"], ["Carriers", "DHL and Bluedart."]],
        }
    )

    try:
        markdown_result = processor.process_document(tmp_path)
        assert "## Billing — Record 1" in markdown_result
        assert "## Shipping — Record 1" in markdown_result
        assert "- **Detail**: DHL and Bluedart." in markdown_result
    finally:
        tmp_path.unlink(missing_ok=True)


def test_xlsx_chunks_stay_self_describing():
    """Every child chunk should carry column names, not bare values."""
    from document_chunker import DocumentChunker

    processor = DocumentProcessor()
    rows = [["Question", "Answer"]] + [
        [f"Question number {i}?", f"Answer number {i}. " * 12] for i in range(40)
    ]
    tmp_path = _write_workbook({"FAQ": rows})

    md_path = None
    try:
        markdown_result = processor.process_document(tmp_path)
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8", delete=False) as tmp:
            tmp.write(markdown_result)
            md_path = Path(tmp.name)

        parents, children = DocumentChunker().create_chunks_single(md_path, source_name="faq.xlsx")

        assert parents and children
        assert all("- **" in chunk.page_content for chunk in children)
    finally:
        tmp_path.unlink(missing_ok=True)
        if md_path is not None:
            md_path.unlink(missing_ok=True)


def test_oversized_document_is_rejected_with_an_estimate():
    """A file too large to embed must fail fast."""
    from core.document_manager import DocumentManager

    DocumentManager._reject_if_too_large("small.csv", 10)  # under the limit: no error

    with pytest.raises(ValueError) as excinfo:
        DocumentManager._reject_if_too_large("large.csv", 150_000)

    message = str(excinfo.value)
    assert "150,000 chunks" in message

