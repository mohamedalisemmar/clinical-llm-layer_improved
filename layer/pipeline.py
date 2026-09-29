"""The intermediary layer, end to end.

    case -> Prompt A (raw answer shown to the clinician)
         -> Function A: structure the raw answer
         -> Function B: signals -> LOW / MODERATE / HIGH
         -> Function D: LLM-as-a-Judge (supplementary; not in the rule)
    Function C: clinician rationale = inspectability view of A fields (UI).
    Function E: clinician feedback (study session).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

import config
from layer.completeness import completeness_signal
from layer.consistency import consistency_signal, prompt_agreement_signal
from layer.contradiction import contradiction_signal
from layer.equivalence import check_equivalence
from layer.generation import generate_baseline, generate_critical, generate_samples
from layer.judge import run_judge
from layer.missing_info import (input_inconsistency_signal, missing_info_signal,
                                verbal_confidence_signal)
from layer.reliability import aggregate
from layer.schemas import LayerOutput


def run_layer(case: dict, client, *, raw_response: Optional[str] = None,
              use_injected: bool = True, n_samples: Optional[int] = None,
              progress: Callable[[str], None] = lambda msg: None) -> LayerOutput:
    calls_before = client.n_calls
    n = n_samples or config.N_SAMPLES

    # 1. The answer the clinician sees (identical in both conditions).
    injected = False
    if raw_response is None and use_injected and case.get("injected_response"):
        raw_response = case["injected_response"]["text"]
        injected = True
    if raw_response is None:
        progress("Generating the baseline answer (Prompt A)")
        raw_response = generate_baseline(case, client)

    # 2. Function A - structuring.
    progress("Structuring the answer")
    structured = structure_response_safe(case, raw_response, client)

    # 3. Function B - reliability signals.
    progress(f"Generating {n} repeated answers (Prompt B)")
    samples = generate_samples(case, client, n)
    progress("Generating the critical-evaluation answer (Prompt C)")
    critical = generate_critical(case, client)

    progress("Comparing diagnoses by meaning")
    candidates = [x.primary_diagnosis or "(no answer)" for x in samples] + \
                 [critical.primary_diagnosis or "(no answer)"]
    same = check_equivalence(structured.primary_diagnosis, candidates, client)
    sample_agreement, agree_c = same[:n], same[n]

    b0 = samples[0] if samples and samples[0].parse_ok else None
    signals = [
        consistency_signal(sample_agreement, samples),
        prompt_agreement_signal(sample_agreement[0] if b0 else None,
                                agree_c if critical.parse_ok else None, b0, critical),
    ]
    progress("Checking for contradictions")
    contra_sig, conflicts = contradiction_signal(case, structured, client)
    signals += [
        contra_sig,
        completeness_signal(structured, samples),
        missing_info_signal(structured),
        input_inconsistency_signal(structured, critical),
        verbal_confidence_signal(structured, critical),
    ]
    reliability = aggregate(signals)

    # 4. Function D - automated quality check (supplementary).
    judge = None
    if config.USE_LLM_JUDGE:
        progress("Running the automated quality check")
        judge = run_judge(case, raw_response, client)

    return LayerOutput(
        case_id=case.get("id", "custom"), provider=client.provider, model=client.model,
        raw_response=raw_response, injected=injected, structured=structured,
        samples=samples, critical=critical, sample_agreement=sample_agreement,
        signals=signals, contradictions=conflicts, reliability=reliability, judge=judge,
        n_llm_calls=client.n_calls - calls_before,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def structure_response_safe(case, raw, client):
    from layer.structuring import structure_response
    return structure_response(case, raw, client)
