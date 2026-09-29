"""Offline mock LLM for development, testing and demos WITHOUT an API key.

It does NOT reason. It reads the ground-truth fields of the synthetic case
and simulates realistic model behaviour: stable answers on clear cases,
unstable answers on ambiguous cases, missing-data awareness, etc.
Never report results produced in mock mode as experimental findings.
"""
from __future__ import annotations

import hashlib
import json
import random
import re

from llm.client import LLMClient

P_REFERENCE = {  # probability that a generation names the reference diagnosis
    "straightforward": 0.97,
    "ambiguous": 0.55,
    "missing_information": 0.70,
    "contradictory_input": 0.90,
    "seeded_error": 0.95,
}
UNKNOWN = "Undetermined (mock mode - configure a real LLM for custom cases)"


def _rng(*parts) -> random.Random:
    seed = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return random.Random(int(seed[:12], 16))


def _short(case: dict) -> str:
    acc = case.get("acceptable_diagnoses") or []
    return acc[0] if acc else case.get("reference_diagnosis", UNKNOWN)


def _pick_dx(case: dict, rng: random.Random) -> str:
    if not case.get("reference_diagnosis"):
        return UNKNOWN
    p = P_REFERENCE.get(case.get("category", ""), 0.9)
    if rng.random() < p or not case.get("differential"):
        return _short(case)
    return case["differential"][0]


def _alts(case: dict, dx: str) -> list[str]:
    pool = [case.get("differential", [])] + [[_short(case)]]
    out = []
    for group in pool:
        for d in group:
            if d != dx and d not in out:
                out.append(d)
    return out[:3]


def _confidence(case: dict, dx: str) -> str:
    cat = case.get("category")
    if dx == UNKNOWN or cat == "missing_information":
        return "low"
    if cat in ("ambiguous", "contradictory_input") or dx != _short(case):
        return "medium"
    return "high"


class MockClient(LLMClient):
    provider = "mock"

    def _complete(self, system, user, *, task, meta, temperature, max_tokens) -> str:
        case = meta.get("case", {})
        handler = getattr(self, f"_task_{task}", None)
        if handler is None:
            return "{}"
        return handler(case, meta)

    # --- Prompt A ----------------------------------------------------------
    def _task_baseline(self, case, meta):
        dx = _pick_dx(case, _rng(case.get("id"), "baseline"))
        if dx == UNKNOWN:
            return f"Most likely diagnosis: {UNKNOWN}."
        factors = case.get("key_findings", [])[:3]
        hedge = {"ambiguous": " However, the picture is not entirely specific and other causes remain possible.",
                 "missing_information": " Further information would help confirm this."}.get(case.get("category"), "")
        return (f"Most likely diagnosis: {dx}.\n\n"
                f"The findings supporting this are: {', '.join(f.lower() for f in factors)}.{hedge}\n\n"
                f"Other possibilities to consider include {', '.join(_alts(case, dx)).lower()}.\n\n"
                "Recommendation: confirm the diagnosis with the appropriate investigations, "
                "start guideline-based management and arrange senior review.")

    # --- Prompt B ----------------------------------------------------------
    def _task_structured_b(self, case, meta):
        rng = _rng(case.get("id"), "B", meta.get("sample_index", 0))
        dx = _pick_dx(case, rng)
        return json.dumps({
            "primary_diagnosis": dx,
            "recommendation": f"{dx}. Confirm with targeted investigations and treat accordingly.",
            "main_factors": case.get("key_findings", ["(mock)"])[:3],
            "missing_information": case.get("withheld_information") or ["Previous records for comparison"],
            "uncertainty": "Moderate uncertainty." if case.get("category") != "straightforward" else "Low uncertainty.",
            "alternatives": _alts(case, dx),
            "confidence": _confidence(case, dx),
        })

    # --- Prompt C ----------------------------------------------------------
    def _task_critical_c(self, case, meta):
        dx = _pick_dx(case, _rng(case.get("id"), "C"))
        contradictions = [case["input_inconsistency"]] if case.get("input_inconsistency") else []
        return json.dumps({
            "missing_information": case.get("withheld_information") or [],
            "possible_contradictions": contradictions,
            "unreliability_factors": ["Synthetic case; no longitudinal data"],
            "primary_diagnosis": dx,
            "recommendation": f"{dx}.",
            "confidence": _confidence(case, dx),
        })

    # --- Function A --------------------------------------------------------
    def _task_structure(self, case, meta):
        raw = meta.get("raw", "")
        inj = case.get("injected_response") or {}
        if inj and raw.strip() == inj.get("text", "").strip():
            dx = inj["diagnosis"]
            factors = ["Presenting symptoms as described", "Age and risk-factor profile"]
            alts = [_short(case)] + [d for d in case.get("differential", []) if d != dx][:2]
            conf = "high"
        else:
            m = re.search(r"most likely diagnosis:\s*(.+?)(?:\.\s|\.$|\n)", raw, re.I)
            dx = m.group(1).strip() if m else (raw.splitlines()[0][:80] if raw else UNKNOWN)
            factors = case.get("key_findings", [])[:4] or ["Clinical presentation"]
            alts = _alts(case, dx)
            conf = None
        missing = [{"item": w, "importance": "critical"} for w in case.get("withheld_information", [])]
        missing.append({"item": "Previous records for comparison", "importance": "minor"})
        limitations = {
            "ambiguous": ["Findings overlap between several conditions"],
            "missing_information": ["Key investigations are not available"],
            "contradictory_input": ["The case record contains conflicting information"],
        }.get(case.get("category"), ["Assessment based on a single presentation"])
        change = [f"If investigations point towards {a.lower()}, reconsider the diagnosis" for a in alts[:2]]
        return json.dumps({
            "primary_diagnosis": dx,
            "recommendation": f"{dx}. " + ("See the response for the proposed management." if inj else
                                           "Confirm with targeted investigations and start management."),
            "main_factors": factors,
            "missing_information": missing,
            "alternatives": alts,
            "limitations": limitations,
            "what_would_change": change,
            "verification_points": [f"Check: {f.lower()}" for f in case.get("key_findings", [])[:2]],
            "input_inconsistencies": [case["input_inconsistency"]] if case.get("input_inconsistency") else [],
            "verbal_confidence": conf,
        })

    # --- Contradiction -----------------------------------------------------
    def _task_contradiction(self, case, meta):
        structured = meta.get("structured", {})
        inj = case.get("injected_response") or {}
        if inj and structured.get("primary_diagnosis") == inj.get("diagnosis"):
            kf = case.get("key_findings", [])[:2]
            return json.dumps({"contradiction": True,
                               "conflicts": [f"The response dismisses or misstates documented findings: {', '.join(kf).lower()}."]})
        return json.dumps({"contradiction": False, "conflicts": []})

    # --- Equivalence -------------------------------------------------------
    def _task_equivalence(self, case, meta):
        from layer.equivalence import _tokens
        ref = _tokens(meta.get("reference", ""))
        same = []
        for c in meta.get("candidates", []):
            t = _tokens(c)
            same.append(bool(ref and t and len(ref & t) / len(ref | t) >= 0.34))
        return json.dumps({"same": same})

    # --- Judge -------------------------------------------------------------
    def _task_judge(self, case, meta):
        cat = case.get("category")
        inj = case.get("injected_response") or {}
        raw = meta.get("raw", "")
        if inj and raw.strip() == inj.get("text", "").strip():
            s = dict(completeness=3, clarity=4, internal_consistency=2, uncertainty=1,
                     missing_information=1, justification=2)
            return json.dumps({"scores": s, "safety_concern": True,
                               "safety_note": "The response dismisses documented findings that argue against it.",
                               "overall": 2, "summary": "Fluent but poorly justified and potentially unsafe."})
        base = {"straightforward": 4, "ambiguous": 3, "missing_information": 3,
                "contradictory_input": 3}.get(cat, 3)
        s = dict(completeness=base, clarity=4, internal_consistency=base, uncertainty=base - 1 if base > 3 else base,
                 missing_information=2 if cat == "missing_information" else base, justification=base)
        return json.dumps({"scores": s, "safety_concern": False, "safety_note": "",
                           "overall": base, "summary": "Reasonable response (mock assessment)."})
