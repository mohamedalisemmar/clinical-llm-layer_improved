"""Export the cases to a spreadsheet a clinician can review before the study.

    python -m scripts.export_case_review      ->  docs/case_review_sheet.csv
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm.prompts import format_case  # noqa: E402
from storage import load_cases  # noqa: E402

out = Path(__file__).resolve().parents[1] / "docs" / "case_review_sheet.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["case_id", "category", "case_as_shown_to_participants", "reference_diagnosis",
                "acceptable_diagnoses", "seeded_wrong_answer", "clinically_realistic (yes/no)",
                "reference_correct (yes/no)", "reviewer_comments"])
    for c in load_cases():
        w.writerow([c["id"], c["category"], format_case(c), c["reference_diagnosis"],
                    "; ".join(c.get("acceptable_diagnoses", [])),
                    (c.get("injected_response") or {}).get("text", ""), "", "", ""])
print(f"Wrote {out}")
