"""Automatic grading of the shown answer against the case ground truth.

Used ONLY for analysis, never by the layer. The researcher should review
the result in data/outputs/adjudication.csv (column output_correct).
"""
from __future__ import annotations

from layer.equivalence import check_equivalence


def auto_grade(case: dict, shown_diagnosis: str, injected: bool, client) -> bool:
    if injected:
        return False
    acceptable = case.get("acceptable_diagnoses") or [case.get("reference_diagnosis", "")]
    return any(check_equivalence(shown_diagnosis, acceptable, client))
