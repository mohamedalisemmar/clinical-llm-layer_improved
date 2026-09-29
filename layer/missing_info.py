"""Function B signals 5-7: missing-information awareness, inconsistencies in the
input data, and verbalised confidence (supplementary only)."""
from __future__ import annotations

from layer.schemas import SampleResponse, Signal, StructuredResponse


def missing_info_signal(s: StructuredResponse) -> Signal:
    critical = [m.item for m in s.missing_information if m.importance == "critical" and m.item]
    minor = [m.item for m in s.missing_information if m.importance == "minor" and m.item]
    if critical:
        return Signal(name="missing_information", label="Missing information", status="warn",
                      value=len(critical),
                      detail="Critical data missing: " + "; ".join(critical[:4]) + ".")
    detail = "No critical data identified as missing."
    if minor:
        detail += f" {len(minor)} minor item(s) noted."
    return Signal(name="missing_information", label="Missing information", status="pass",
                  value=0, detail=detail)


def input_inconsistency_signal(s: StructuredResponse, critical: SampleResponse | None) -> Signal:
    items = list(s.input_inconsistencies)
    if critical and critical.parse_ok:
        items += [c for c in critical.possible_contradictions
                  if c and any(k in c.lower() for k in ("record", "note", "documented", "history", "case", "states"))]
    items = list(dict.fromkeys(i for i in items if i.strip()))
    if items:
        return Signal(name="input_inconsistency", label="Inconsistencies in the case data",
                      status="warn", value=len(items), detail="; ".join(items[:2]))
    return Signal(name="input_inconsistency", label="Inconsistencies in the case data",
                  status="pass", value=0, detail="No conflicting facts found in the case data.")


def verbal_confidence_signal(s: StructuredResponse, critical: SampleResponse | None) -> Signal:
    conf = None
    if critical and critical.confidence:
        conf = str(critical.confidence).lower().strip()
    conf = conf or s.verbal_confidence
    if conf == "moderate":
        conf = "medium"
    if conf not in {"low", "medium", "high"}:
        return Signal(name="verbal_confidence", label="Model's stated confidence (supplementary)",
                      status="na", detail="The model did not state a confidence level.")
    status = "warn" if conf == "low" else "pass"
    return Signal(name="verbal_confidence", label="Model's stated confidence (supplementary)",
                  status=status, value=conf,
                  detail=f"The model describes its own confidence as {conf}. "
                         "This is not a calibrated probability.")
