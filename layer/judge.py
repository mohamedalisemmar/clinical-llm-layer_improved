"""Function D - LLM-as-a-Judge. Supplementary screening only, never ground truth."""
from __future__ import annotations

from llm import prompts
from llm.json_utils import JSONParseError, call_json
from layer.schemas import JudgeResult


def run_judge(case: dict, raw: str, client) -> JudgeResult:
    try:
        data = call_json(client, prompts.SYSTEM_ANALYST,
                         prompts.fill(prompts.PROMPT_JUDGE, case=prompts.format_case(case), raw=raw),
                         task="judge", meta={"case": case, "raw": raw})
        scores = {k: float(v) for k, v in (data.get("scores") or {}).items()
                  if isinstance(v, (int, float, str)) and str(v).replace(".", "", 1).isdigit()}
        overall = data.get("overall")
        return JudgeResult(scores=scores, safety_concern=bool(data.get("safety_concern")),
                           safety_note=str(data.get("safety_note") or ""),
                           overall=float(overall) if overall is not None else None,
                           summary=str(data.get("summary") or ""))
    except (JSONParseError, ValueError, AttributeError, TypeError):
        return JudgeResult(available=False, summary="Automated quality check unavailable.")
