"""Function B signal 3: contradiction detection (rule-based + optional LLM check)."""
from __future__ import annotations

import re

import config
from llm import prompts
from llm.json_utils import JSONParseError, call_json
from layer.equivalence import normalize, rule_same
from layer.schemas import Signal, StructuredResponse

_NEGATIONS = ("unlikely", "ruled out", "excluded", "not consistent with", "can be discounted")


def rule_based_contradictions(s: StructuredResponse) -> list[str]:
    found = []
    dx = s.primary_diagnosis
    if not dx:
        return found
    for alt in s.alternatives:
        if rule_same(dx, alt) is True:
            found.append(f"'{dx}' is given both as the main diagnosis and as an alternative.")
            break
    dx_norm = normalize(dx)
    for text in s.limitations + s.main_factors:
        t = normalize(text)
        if dx_norm and dx_norm in t and any(neg in text.lower() for neg in _NEGATIONS):
            found.append(f"The response states its own diagnosis is unlikely or excluded: \"{text}\"")
    return found


def llm_contradictions(case: dict, s: StructuredResponse, client) -> list[str]:
    try:
        data = call_json(client, prompts.SYSTEM_ANALYST,
                         prompts.fill(prompts.PROMPT_CONTRADICTION, case=prompts.format_case(case),
                                      structured=prompts.structured_to_text(s.model_dump())),
                         task="contradiction", meta={"case": case, "structured": s.model_dump()})
    except (JSONParseError, ValueError):
        return []
    if isinstance(data, dict) and data.get("contradiction"):
        conflicts = [str(c) for c in data.get("conflicts", []) if str(c).strip()]
        return conflicts or ["The response conflicts with itself or with the case data."]
    return []


def contradiction_signal(case: dict, s: StructuredResponse, client) -> tuple[Signal, list[str]]:
    conflicts = rule_based_contradictions(s)
    if config.USE_LLM_CONTRADICTION_CHECK:
        conflicts += llm_contradictions(case, s, client)
    conflicts = list(dict.fromkeys(conflicts))  # de-duplicate, keep order
    if conflicts:
        return (Signal(name="contradiction", label="Contradictions", status="fail", value=True,
                       detail=conflicts[0] + (f" (+{len(conflicts) - 1} more)" if len(conflicts) > 1 else "")),
                conflicts)
    return (Signal(name="contradiction", label="Contradictions", status="pass", value=False,
                   detail="No contradiction found within the response or against the case data."), [])
