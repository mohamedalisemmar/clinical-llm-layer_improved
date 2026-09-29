"""Function A - output structuring.

Turns the free-text answer into fixed clinician-oriented fields while keeping
the recommendation exactly as the model stated it (so Condition A and B show
the same recommendation, which keeps the experiment fair).
"""
from __future__ import annotations

from llm import prompts
from llm.json_utils import JSONParseError, call_json
from layer.schemas import StructuredResponse


def structure_response(case: dict, raw: str, client) -> StructuredResponse:
    try:
        data = call_json(
            client, prompts.SYSTEM_ANALYST,
            prompts.fill(prompts.PROMPT_STRUCTURE, case=prompts.format_case(case), raw=raw),
            task="structure", meta={"case": case, "raw": raw}, temperature=0.0,
        )
        return StructuredResponse.model_validate(data)
    except (JSONParseError, ValueError):
        # Fallback: keep the raw text as the recommendation so nothing is lost.
        first = raw.strip().splitlines()[0] if raw.strip() else ""
        return StructuredResponse(primary_diagnosis=first[:120], recommendation=raw[:600])
