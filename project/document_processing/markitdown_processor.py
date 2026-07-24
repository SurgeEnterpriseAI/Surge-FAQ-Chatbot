import os
from pathlib import Path
import logging

logger = logging.getLogger("document_processor")

class DocumentProcessor:
    def __init__(self):
        # Lazy import MarkItDown to avoid import issues on startup if not fully installed yet
        self._markitdown = None

    @property
    def markitdown(self):
        if self._markitdown is None:
            try:
                from markitdown import MarkItDown
                self._markitdown = MarkItDown()
            except ImportError as e:
                logger.error("Failed to import MarkItDown. Make sure it is installed.")
                raise e
        return self._markitdown

    @staticmethod
    def _clean_cell(value) -> str:
        """Normalise a single table cell to a single-line string."""
        if value is None:
            return ""
        text = str(value)
        if text.strip().lower() in {"nan", "nat", "none"}:
            return ""
        return text.replace("\r", " ").replace("\n", " ").strip()

    @classmethod
    def _rows_to_records(cls, headers, rows, sheet_name: str = None) -> list:
        """Render tabular rows as self-describing Markdown records.

        Pipe tables lose their header row as soon as the chunker splits them, so
        every row becomes its own ``## Record`` section with the column name
        attached to each value. That keeps a child chunk interpretable on its own.
        """
        headers_cleaned = [cls._clean_cell(h) for h in headers]
        label = f"{sheet_name} — Record" if sheet_name else "Record"

        lines = []
        row_idx = 1
        for row in rows:
            cells = [cls._clean_cell(cell) for cell in row]
            if not any(cells):
                continue
            lines.append(f"## {label} {row_idx}")
            for header, cell in zip(headers_cleaned, cells):
                if cell:
                    lines.append(f"- **{header}**: {cell}")
            lines.append("")
            row_idx += 1
        return lines

    def _convert_spreadsheet(self, file_path: Path, suffix: str) -> str:
        """Converts XLSX/XLS sheets to record-per-row Markdown."""
        import pandas as pd

        engine = "openpyxl" if suffix == ".xlsx" else "xlrd"
        sheets = pd.read_excel(file_path, sheet_name=None, dtype=str, header=None, engine=engine)

        multi_sheet = len(sheets) > 1
        markdown_lines = []
        for sheet_name, frame in sheets.items():
            rows = frame.values.tolist()
            if not rows:
                continue
            headers, body = rows[0], rows[1:]
            markdown_lines.extend(
                self._rows_to_records(headers, body, sheet_name if multi_sheet else None)
            )

        markdown_doc = "\n".join(markdown_lines)
        if not markdown_doc.strip():
            raise ValueError(f"Empty spreadsheet: {file_path.name}")
        return markdown_doc

    def convert_to_markdown(self, file_path: Path) -> str:
        """Converts the given document to markdown using MarkItDown or direct reading."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()
        supported_suffixes = {".pdf", ".docx", ".pptx", ".txt", ".md", ".csv", ".xlsx", ".xls"}
        if suffix not in supported_suffixes:
            raise ValueError(f"Unsupported file type: {suffix}")

        # Check for empty files
        if file_path.stat().st_size == 0:
            raise ValueError(f"Empty document: {file_path.name}")

        # Handle Markdown files directly to preserve original content without modifications
        if suffix == ".md":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if not content.strip():
                    raise ValueError(f"Empty document: {file_path.name}")
                return content
            except Exception as e:
                raise ValueError(f"Failed to read Markdown file: {e}")

        # Handle TXT files directly to ensure proper UTF-8 reading and format preservation
        if suffix == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if not content.strip():
                    raise ValueError(f"Empty document: {file_path.name}")
                return content
            except Exception as e:
                raise ValueError(f"Failed to read TXT file: {e}")

        # Handle CSV files directly to avoid encoding issues and control table generation
        if suffix == ".csv":
            try:
                content = None
                for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
                    try:
                        with open(file_path, "r", encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                import csv
                import io
                import sys

                try:
                    csv.field_size_limit(sys.maxsize)
                except Exception:
                    pass

                f_in = io.StringIO(content)
                try:
                    sample = "\n".join([line for line in content.splitlines()[:50] if line.strip()])
                    dialect = csv.Sniffer().sniff(sample)
                except Exception:
                    dialect = 'excel'

                reader = csv.reader(f_in, dialect=dialect)

                markdown_lines = []
                headers = next(reader, None)
                if headers:
                    markdown_lines = self._rows_to_records(headers, reader)

                markdown_doc = "\n".join(markdown_lines)
                if not markdown_doc.strip():
                    raise ValueError(f"Empty CSV file: {file_path.name}")
                return markdown_doc
            except Exception as e:
                raise ValueError(f"Failed to convert CSV (possibly corrupted or invalid): {e}")

        # Handle spreadsheets directly. MarkItDown renders each sheet as one large
        # pipe table, which the chunker later cuts into headerless row fragments
        # that retrieve poorly; record-per-row keeps every chunk self-describing.
        if suffix in (".xlsx", ".xls"):
            try:
                return self._convert_spreadsheet(file_path, suffix)
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(
                    f"Failed to convert {suffix.lstrip('.').upper()} (possibly corrupted or invalid): {e}"
                )

        # Use MarkItDown for PDF, DOCX, PPTX
        try:
            result = self.markitdown.convert(str(file_path))
            if not result or not result.text_content:
                raise ValueError("MarkItDown conversion returned empty result.")
            
            content = result.text_content
            if not content.strip():
                raise ValueError(f"Empty document contents after conversion: {file_path.name}")
            return content
        except Exception as e:
            # Check if file might be corrupted
            if suffix in (".pdf", ".docx", ".pptx"):
                raise ValueError(
                    f"Failed to convert {suffix.lstrip('.').upper()} (possibly corrupted): {e}"
                )
            raise ValueError(f"Conversion failure for {file_path.name}: {e}")

    def process_document(self, file_path: Path) -> str:
        """Processes document and returns the markdown string. This method is the main entry point."""
        file_path = Path(file_path)
        return self.convert_to_markdown(file_path)

    def cleanup_temp_file(self, file_path: Path) -> None:
        """Deletes the temporary file if it exists and is under the uploads directory."""
        if not file_path:
            return
        
        file_path = Path(file_path)
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                logger.info(f"Successfully cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary file {file_path}: {e}")
