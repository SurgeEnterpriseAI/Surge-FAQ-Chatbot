import csv
import re
from pathlib import Path

def convert_md_to_csv(md_path: Path, output_csv_path: Path):
    if not md_path.exists():
        print(f"Source file {md_path} does not exist.")
        return 0

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    current_record = {}

    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str.startswith("## Record"):
                if current_record and ("question" in current_record or "answer" in current_record):
                    records.append(current_record)
                current_record = {}
            elif line_str.startswith("- **question**:") or line_str.startswith("- **Question** logic:"):
                match = re.match(r"^-\s*\*\*(?:question|Question)\*\*\s*:\s*(.*)$", line_str, re.IGNORECASE)
                if match:
                    current_record["question"] = match.group(1).strip()
            elif line_str.startswith("- **answer**:") or line_str.startswith("- **Answer** logic:"):
                match = re.match(r"^-\s*\*\*(?:answer|Answer)\*\*\s*:\s*(.*)$", line_str, re.IGNORECASE)
                if match:
                    current_record["answer"] = match.group(1).strip()
            elif line_str.startswith("- **source**:") or line_str.startswith("- **Source** logic:"):
                match = re.match(r"^-\s*\*\*(?:source|Source)\*\*\s*:\s*(.*)$", line_str, re.IGNORECASE)
                if match:
                    current_record["source"] = match.group(1).strip()
            elif line_str.startswith("- **focus_area**:") or line_str.startswith("- **focus**:") or line_str.startswith("- **Focus Area** logic:"):
                match = re.match(r"^-\s*\*\*(?:focus_area|focus|Focus Area)\*\*\s*:\s*(.*)$", line_str, re.IGNORECASE)
                if match:
                    current_record["focus_area"] = match.group(1).strip()
            elif line_str.startswith("- **question_type**:") or line_str.startswith("- **type**:"):
                match = re.match(r"^-\s*\*\*(?:question_type|type)\*\*\s*:\s*(.*)$", line_str, re.IGNORECASE)
                if match:
                    current_record["question_type"] = match.group(1).strip()
            elif current_record and "answer" in current_record and line_str and not line_str.startswith("- **"):
                current_record["answer"] += " " + line_str

        if current_record and ("question" in current_record or "answer" in current_record):
            records.append(current_record)

    fieldnames = ["question", "answer", "source", "focus_area", "question_type"]
    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "question": r.get("question", "").strip(),
                "answer": r.get("answer", "").strip(),
                "source": r.get("source", "").strip(),
                "focus_area": r.get("focus_area", "").strip(),
                "question_type": r.get("question_type", "").strip(),
            })

    print(f"Successfully converted {len(records):,} records to {output_csv_path}")
    return len(records)

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    md_file = base_dir / "archived_markdown" / "medquad.md"
    csv_file = base_dir / "knowledge_base" / "medquad.csv"
    convert_md_to_csv(md_file, csv_file)
