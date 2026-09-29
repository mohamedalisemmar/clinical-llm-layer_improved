"""Function B - aggregation of the signals into a coarse, explained indicator.

This is the rule from Chapter 1, Section 3.4.2, implemented exactly:

  LOW       if consistency fails OR a clear contradiction is detected
            (either one alone is enough to warn the clinician).
  HIGH      requires (i) consistency across repeated generations,
            (ii) agreement across prompts, (iii) no contradiction,
            (iv) structural completeness - AND nothing that caps it:
            critical missing information, conflicting case data, or a
            model that itself states low confidence.
  MODERATE  every other combination, including "stable but incomplete".

Verbalised confidence can only pull HIGH down to MODERATE; it can never
raise the level. The LLM-as-a-Judge is deliberately NOT part of the rule
(it is shown separately as a supplementary check). No number is ever shown.
"""
from __future__ import annotations

from layer.schemas import ReliabilityResult, Signal


def _get(signals: dict[str, Signal], name: str) -> Signal:
    return signals.get(name) or Signal(name=name, label=name, status="na")


def aggregate(signal_list: list[Signal]) -> ReliabilityResult:
    s = {x.name: x for x in signal_list}
    cons, agree = _get(s, "consistency"), _get(s, "prompt_agreement")
    contra, compl = _get(s, "contradiction"), _get(s, "completeness")
    missing, incons, verbal = _get(s, "missing_information"), _get(s, "input_inconsistency"), _get(s, "verbal_confidence")

    # ---- LOW ---------------------------------------------------------------
    low = []
    if cons.status == "fail":
        agreed, total = cons.detail.split(" repeated")[0].split(" of ")
        low.append(f"none of the {total} repeated answers reproduced this diagnosis" if agreed.strip() == "0"
                   else f"only {agreed} of {total} repeated answers reproduced this diagnosis")
    if contra.status == "fail":
        low.append(f"a contradiction was found: {contra.detail}")
    if low:
        text = "Low: " + "; ".join(low)
        return ReliabilityResult(level="LOW", explanation=_sentence(text) + " Verify independently before acting.",
                                 reasons=low, verify_independently=True)

    # ---- HIGH requirements -----------------------------------------------
    unmet = []
    if cons.status != "pass":
        unmet.append("the answer was not fully stable across repeated generations"
                     if cons.status == "warn" else "consistency could not be measured")
    if agree.status != "pass":
        unmet.append("the alternative prompts did not all agree"
                     if agree.status in ("warn", "fail") else "prompt agreement could not be measured")
    if compl.status != "pass":
        unmet.append("some requested fields were empty")

    caps = []
    if missing.status == "warn":
        items = missing.detail.replace("Critical data missing: ", "").rstrip(".").split("; ")
        caps.append("key information is missing (" + ", ".join(items[:3]).lower() + ("..." if len(items) > 3 else "") + ")")
    if incons.status == "warn":
        caps.append("the case data contain conflicting facts")
    if verbal.status == "warn":
        caps.append("the model itself states low confidence")

    positives = []
    if cons.status == "pass":
        positives.append("consistent across repeated answers")
    if agree.status == "pass":
        positives.append("the alternative prompts agreed")
    if contra.status == "pass":
        positives.append("no contradictions found")

    if not unmet and not caps:
        text = "High: " + _join(positives)
        return ReliabilityResult(level="HIGH", explanation=_sentence(text), reasons=positives)

    negatives = unmet + caps
    text = "Moderate: " + (_join(positives[:2]) + ", but " if positives else "") + _join(negatives)
    return ReliabilityResult(level="MODERATE", explanation=_sentence(text), reasons=negatives)


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith(".") else text + "."
