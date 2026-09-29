"""Function B signal 4: structural completeness (instruction adherence proxy)."""
from __future__ import annotations

from layer.schemas import SampleResponse, Signal, StructuredResponse

CARD_FIELDS = {
    "recommendation": "recommendation",
    "main_factors": "main factors",
    "alternatives": "alternatives",
    "limitations": "limitations",
    "what_would_change": "what would change the recommendation",
}
SAMPLE_FIELDS = ["primary_diagnosis", "recommendation", "main_factors", "missing_information",
                 "uncertainty", "alternatives"]


def completeness_signal(s: StructuredResponse, samples: list[SampleResponse]) -> Signal:
    empty = [label for f, label in CARD_FIELDS.items() if not getattr(s, f)]
    complete_samples = sum(
        1 for x in samples if x.parse_ok and all(getattr(x, f) for f in SAMPLE_FIELDS))
    sample_rate = complete_samples / len(samples) if samples else 1.0

    if not empty and sample_rate >= 0.8:
        return Signal(name="completeness", label="Completeness of requested fields", status="pass",
                      value=round(sample_rate, 3),
                      detail="All requested fields were populated.")
    parts = []
    if empty:
        parts.append("empty field(s): " + ", ".join(empty))
    if sample_rate < 0.8:
        parts.append(f"only {complete_samples}/{len(samples)} structured answers filled every field")
    status = "fail" if len(empty) >= 2 else "warn"
    return Signal(name="completeness", label="Completeness of requested fields", status=status,
                  value=round(sample_rate, 3), detail="; ".join(parts).capitalize() + ".")
