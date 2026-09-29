"""Semantic equivalence of diagnosis names.

Consistency must be measured by MEANING, not exact wording
("STEMI" == "ST-elevation myocardial infarction"). A cheap rule-based
matcher runs first; an LLM check is used for the remaining pairs.
"""
from __future__ import annotations

import re

import config
from llm import prompts
from llm.json_utils import JSONParseError, call_json

_STOP = {"acute", "suspected", "likely", "possible", "probable", "the", "a", "of", "with",
         "and", "due", "to", "left", "right", "disease", "early",
         "severe", "mild", "bilateral", "in", "on", "from", "secondary", "(", ")"}

_SYNONYMS = {
    "stemi": "st elevation myocardial infarction",
    "mi": "myocardial infarction",
    "ami": "acute myocardial infarction",
    "nstemi": "non st elevation myocardial infarction",
    "dka": "diabetic ketoacidosis",
    "pe": "pulmonary embolism",
    "dvt": "deep vein thrombosis",
    "sah": "subarachnoid haemorrhage",
    "sle": "systemic lupus erythematosus",
    "uti": "urinary tract infection",
    "cap": "community acquired pneumonia",
    "acs": "acute coronary syndrome",
    "hf": "heart failure",
    "copd": "chronic obstructive pulmonary disease",
    "gad": "generalised anxiety disorder",
}


def normalize(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("hemorrhage", "haemorrhage").replace("anemia", "anaemia").replace("ischemic", "ischaemic")
    t = t.replace("hypoglycemia", "hypoglycaemia").replace("generalized", "generalised")
    t = re.sub(r"[^a-z0-9 ]+", " ", t.replace("-", " "))
    words = [_SYNONYMS.get(w, w) for w in t.split()]
    return " ".join(words).strip()


def _tokens(text: str) -> set[str]:
    return {w for w in normalize(text).split() if w not in _STOP and len(w) > 1}


def rule_same(a: str, b: str) -> bool | None:
    """True / False when confident, None when unsure (defer to the LLM)."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return None
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if small <= big:
        # "acute inferior STEMI" vs "STEMI" -> same; but a single shared word
        # ("hypothyroidism" vs "subclinical hypothyroidism") is ambiguous.
        return True if (len(small) >= 2 or small == big) else None
    jac = len(ta & tb) / len(ta | tb)
    if jac >= 0.6:
        return True
    if jac == 0:
        return False
    return None


def check_equivalence(reference: str, candidates: list[str], client) -> list[bool]:
    results: list[bool | None] = [rule_same(reference, c) for c in candidates]
    unsure = [i for i, r in enumerate(results) if r is None]
    if unsure and config.USE_LLM_EQUIVALENCE:
        todo = [candidates[i] for i in unsure]
        listing = "\n".join(f"{k + 1}. {c}" for k, c in enumerate(todo))
        try:
            data = call_json(client, prompts.SYSTEM_ANALYST,
                             prompts.fill(prompts.PROMPT_EQUIVALENCE, reference=reference, candidates=listing),
                             task="equivalence", meta={"reference": reference, "candidates": todo})
            same = data.get("same", []) if isinstance(data, dict) else data
            for i, val in zip(unsure, same):
                results[i] = bool(val)
        except (JSONParseError, ValueError, AttributeError):
            pass
    # Anything still unsure: partial token overlap counts as the same condition.
    final = []
    for c, r in zip(candidates, results):
        if r is None:
            ta, tb = _tokens(reference), _tokens(c)
            r = bool(ta and tb and len(ta & tb) / len(ta | tb) >= 0.34)
        final.append(bool(r))
    return final
