"""Pydantic data structures for the intermediary layer."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Status = Literal["pass", "warn", "fail", "na"]
Level = Literal["LOW", "MODERATE", "HIGH"]


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    return v


class MissingItem(BaseModel):
    item: str
    importance: Literal["critical", "minor"] = "minor"


class StructuredResponse(BaseModel):
    """Function A output: structured fields (input to Function C presentation)."""
    primary_diagnosis: str = ""
    recommendation: str = ""
    main_factors: list[str] = Field(default_factory=list)
    missing_information: list[MissingItem] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    what_would_change: list[str] = Field(default_factory=list)
    verification_points: list[str] = Field(default_factory=list)
    input_inconsistencies: list[str] = Field(default_factory=list)
    verbal_confidence: Optional[Literal["low", "medium", "high"]] = None

    @field_validator("main_factors", "alternatives", "limitations", "what_would_change",
                     "verification_points", "input_inconsistencies", mode="before")
    @classmethod
    def _lists(cls, v):
        return _as_list(v)

    @field_validator("missing_information", mode="before")
    @classmethod
    def _missing(cls, v):
        out = []
        for x in _as_list(v):
            if isinstance(x, str):
                out.append({"item": x, "importance": "minor"})
            elif isinstance(x, dict):
                imp = str(x.get("importance", "minor")).lower()
                out.append({"item": x.get("item", ""), "importance": "critical" if "crit" in imp else "minor"})
        return out

    @field_validator("verbal_confidence", mode="before")
    @classmethod
    def _conf(cls, v):
        if v is None:
            return None
        v = str(v).strip().lower()
        if v in {"moderate"}:
            return "medium"
        return v if v in {"low", "medium", "high"} else None


class SampleResponse(BaseModel):
    """Output of Prompt B (repeated generations) or Prompt C."""
    primary_diagnosis: str = ""
    recommendation: str = ""
    main_factors: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    uncertainty: str = ""
    alternatives: list[str] = Field(default_factory=list)
    possible_contradictions: list[str] = Field(default_factory=list)
    unreliability_factors: list[str] = Field(default_factory=list)
    confidence: Optional[str] = None
    parse_ok: bool = True

    @field_validator("main_factors", "missing_information", "alternatives",
                     "possible_contradictions", "unreliability_factors", mode="before")
    @classmethod
    def _lists(cls, v):
        return [x if isinstance(x, str) else str(x.get("item", x)) if isinstance(x, dict) else str(x)
                for x in _as_list(v)]


class Signal(BaseModel):
    name: str
    label: str
    status: Status
    value: Optional[float | str | bool] = None
    detail: str = ""


class ReliabilityResult(BaseModel):
    level: Level
    explanation: str
    reasons: list[str] = Field(default_factory=list)
    verify_independently: bool = False


class JudgeResult(BaseModel):
    scores: dict[str, float] = Field(default_factory=dict)
    safety_concern: bool = False
    safety_note: str = ""
    overall: Optional[float] = None
    summary: str = ""
    available: bool = True


class LayerOutput(BaseModel):
    case_id: str
    provider: str
    model: str
    raw_response: str
    injected: bool = False
    structured: StructuredResponse
    samples: list[SampleResponse] = Field(default_factory=list)
    critical: Optional[SampleResponse] = None
    sample_agreement: list[bool] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    reliability: ReliabilityResult
    judge: Optional[JudgeResult] = None
    n_llm_calls: int = 0
    created_at: str = ""
