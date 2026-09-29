"""Function B signals 1 & 2: consistency across repeated generations and
agreement across prompting strategies (Prompt A vs B vs C)."""
from __future__ import annotations

import config
from layer.schemas import SampleResponse, Signal


def consistency_signal(agreement: list[bool], samples: list[SampleResponse]) -> Signal:
    valid = [a for a, s in zip(agreement, samples) if s.parse_ok and s.primary_diagnosis]
    if not valid:
        return Signal(name="consistency", label="Consistency across repeated answers",
                      status="na", detail="No valid repeated generations were available.")
    rate = sum(valid) / len(valid)
    if rate >= config.CONSISTENCY_PASS:
        status = "pass"
    elif rate >= config.CONSISTENCY_WARN:
        status = "warn"
    else:
        status = "fail"
    others = sorted({s.primary_diagnosis for a, s in zip(agreement, samples) if s.parse_ok and not a})
    detail = f"{sum(valid)} of {len(valid)} repeated answers gave the same diagnosis."
    if others:
        detail += " Other answers: " + "; ".join(others[:3]) + "."
    return Signal(name="consistency", label="Consistency across repeated answers",
                  status=status, value=round(rate, 3), detail=detail)


def prompt_agreement_signal(agree_b: bool | None, agree_c: bool | None,
                            b: SampleResponse | None, c: SampleResponse | None) -> Signal:
    votes = [v for v in (agree_b, agree_c) if v is not None]
    if not votes:
        return Signal(name="prompt_agreement", label="Agreement across prompting strategies",
                      status="na", detail="Alternative prompts did not return a usable answer.")
    n_agree = sum(votes)
    if n_agree == len(votes):
        status, detail = "pass", "The structured and critical prompts reached the same diagnosis."
    elif n_agree == 0:
        status = "fail"
        detail = "Neither alternative prompt reached the same diagnosis"
        alts = [x.primary_diagnosis for x in (b, c) if x and x.primary_diagnosis]
        detail += f" (they suggested: {'; '.join(sorted(set(alts)))})." if alts else "."
    else:
        status = "warn"
        dissent = b if agree_b is False else c
        detail = "Only one of the two alternative prompts agreed"
        detail += f"; the other suggested {dissent.primary_diagnosis}." if dissent and dissent.primary_diagnosis else "."
    return Signal(name="prompt_agreement", label="Agreement across prompting strategies",
                  status=status, value=f"{n_agree}/{len(votes)}", detail=detail)
