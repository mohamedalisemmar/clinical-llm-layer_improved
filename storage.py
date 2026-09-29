"""CSV storage for study data (simple, portable, opens in Excel)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import config

RESPONSES_CSV = config.RESULTS_DIR / "responses.csv"
QUESTIONNAIRES_CSV = config.RESULTS_DIR / "questionnaires.csv"
SESSIONS_CSV = config.RESULTS_DIR / "sessions.csv"

RESPONSE_FIELDS = [
    "timestamp", "participant_id", "group", "block", "condition", "case_id", "category",
    "case_set", "shown_diagnosis", "layer_reliability", "decision", "agreement",
    "perceived_reliability", "indicator_appropriateness", "explanation_usefulness",
    "decision_confidence", "main_factor_recall", "missing_info_noted", "own_diagnosis",
    "comments", "time_seconds", "verify_prompt_shown",
]
QUESTIONNAIRE_FIELDS = (
    ["timestamp", "participant_id", "group", "block", "condition"]
    + [f"sus_{i}" for i in range(1, 11)]
    + ["tlx_mental", "tlx_physical", "tlx_temporal", "tlx_performance", "tlx_effort", "tlx_frustration"]
    + ["trust_1", "trust_2", "trust_3"]
)
SESSION_FIELDS = ["timestamp", "participant_id", "group", "role", "experience_years",
                  "specialty", "ai_familiarity", "consent", "preferred_condition", "final_comments", "event"]


def append_row(path: Path, row: dict, fields: list[str]) -> None:
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def load_cases() -> list[dict]:
    return json.loads(config.CASES_PATH.read_text(encoding="utf-8"))["cases"]


def load_output(case_id: str) -> dict | None:
    p = config.OUTPUTS_DIR / f"{case_id}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def outputs_meta() -> dict:
    p = config.OUTPUTS_DIR / "_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
