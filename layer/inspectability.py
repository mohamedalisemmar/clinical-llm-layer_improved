"""Function C - clinician-oriented inspectability.

Builds a presentation view-model from Function A fields.
Does not call the LLM and does not change the reliability rule (Function B).
No raw chain-of-thought is included.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from layer.schemas import StructuredResponse

_MAX_ITEMS = 5
_MAX_CHARS = 120
_EMPTY = "None stated"


def _trim(items: list[str], *, empty: str = _EMPTY) -> list[str]:
    out = []
    for x in items:
        t = " ".join(str(x).split())
        if not t:
            continue
        out.append(t if len(t) <= _MAX_CHARS else t[: _MAX_CHARS - 1] + "…")
        if len(out) >= _MAX_ITEMS:
            break
    return out or [empty]


class ClinicianRationale(BaseModel):
    """Function C output: ordered sections for the clinician UI."""
    primary_diagnosis: str = ""
    recommendation: str = ""
    main_factors: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)  # display strings
    alternatives: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    what_would_change: list[str] = Field(default_factory=list)
    verification_points: list[str] = Field(default_factory=list)
    input_inconsistencies: list[str] = Field(default_factory=list)


def build_rationale(structured: StructuredResponse | dict) -> ClinicianRationale:
    """Map Function A fields → Function C view (theory: inspectable rationale)."""
    if isinstance(structured, dict):
        s = StructuredResponse.model_validate(structured)
    else:
        s = structured

    missing_disp = []
    for m in s.missing_information:
        item = (m.item or "").strip()
        if not item:
            continue
        label = item if len(item) <= _MAX_CHARS else item[: _MAX_CHARS - 1] + "…"
        if m.importance == "critical":
            label = f"{label} (critical)"
        missing_disp.append(label)
        if len(missing_disp) >= _MAX_ITEMS:
            break
    if not missing_disp:
        missing_disp = ["No missing information identified"]

    return ClinicianRationale(
        primary_diagnosis=(s.primary_diagnosis or "").strip(),
        recommendation=(s.recommendation or "").strip(),
        main_factors=_trim(s.main_factors),
        missing_information=missing_disp,
        alternatives=_trim(s.alternatives),
        limitations=_trim(s.limitations),
        what_would_change=_trim(
            s.what_would_change,
            empty="None stated — consider what would falsify this diagnosis",
        ),
        verification_points=_trim(
            s.verification_points,
            empty="None stated — verify key findings before acting",
        ),
        input_inconsistencies=_trim(s.input_inconsistencies, empty=""),
    )