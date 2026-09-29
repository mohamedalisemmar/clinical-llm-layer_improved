"""Checks that the analysis runs on a small fabricated dataset (test fixture only)."""
import random

import evaluation.analysis as an
from evaluation.metrics import sus_score
from storage import QUESTIONNAIRE_FIELDS, RESPONSE_FIELDS, append_row, load_cases


def test_sus_score_bounds():
    assert sus_score([5, 1] * 5) == 100
    assert sus_score([1, 5] * 5) == 0


def test_analysis_runs(tmp_path, monkeypatch):
    resp, quest = tmp_path / "r.csv", tmp_path / "q.csv"
    monkeypatch.setattr(an, "RESPONSES_CSV", resp)
    monkeypatch.setattr(an, "QUESTIONNAIRES_CSV", quest)
    rng = random.Random(0)
    cases = load_cases()
    for p in range(6):
        for cond in "AB":
            for c in rng.sample(cases, 8):
                seeded = c["category"] == "seeded_error"
                accept = rng.random() < (0.3 if seeded and cond == "B" else 0.7 if seeded else 0.85)
                append_row(resp, {"participant_id": f"P{p}", "condition": cond, "case_id": c["id"],
                                  "category": c["category"], "decision": "accept" if accept else "reject",
                                  "agreement": "Agree", "perceived_reliability": "High",
                                  "indicator_appropriateness": "Appropriate" if cond == "B" else "",
                                  "explanation_usefulness": 4, "decision_confidence": 4,
                                  "time_seconds": rng.uniform(40, 120)}, RESPONSE_FIELDS)
            row = {"participant_id": f"P{p}", "condition": cond}
            row.update({f"sus_{i}": rng.randint(1, 5) for i in range(1, 11)})
            row.update({k: rng.randint(10, 80) for k in an.TLX_COLS})
            row.update({f"trust_{i}": rng.randint(1, 5) for i in range(1, 4)})
            append_row(quest, row, QUESTIONNAIRE_FIELDS)
    res = an.run_analysis(save=False)
    assert res["n_participants"] == 6
    assert set(res["main_table"].columns) == {"LLM only", "LLM + layer"}
    assert "reliance_by_condition" in res["figures"]
