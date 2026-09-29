"""Generating the answers: Prompt A (shown), Prompt B (repeated), Prompt C (critical)."""
from __future__ import annotations

import config
from llm import prompts
from llm.json_utils import JSONParseError, call_json
from layer.schemas import SampleResponse


def generate_baseline(case: dict, client) -> str:
    """Prompt A: the unstructured answer that the clinician sees in BOTH conditions."""
    return client.complete(
        prompts.SYSTEM_CLINICAL,
        prompts.fill(prompts.PROMPT_A, case=prompts.format_case(case)),
        task="baseline", meta={"case": case}, temperature=config.BASELINE_TEMPERATURE,
    ).strip()


def _sample(case, client, template, task, index, temperature) -> SampleResponse:
    try:
        data = call_json(client, prompts.SYSTEM_JSON,
                         prompts.fill(template, case=prompts.format_case(case)),
                         task=task, meta={"case": case, "sample_index": index},
                         temperature=temperature)
        return SampleResponse.model_validate(data)
    except (JSONParseError, ValueError):
        return SampleResponse(parse_ok=False)


def generate_samples(case: dict, client, n: int | None = None) -> list[SampleResponse]:
    """Prompt B repeated n times at high temperature (consistency signal)."""
    n = n or config.N_SAMPLES
    return [_sample(case, client, prompts.PROMPT_B, "structured_b", i, config.SAMPLE_TEMPERATURE)
            for i in range(n)]


def generate_critical(case: dict, client) -> SampleResponse:
    """Prompt C once (prompt-agreement signal)."""
    return _sample(case, client, prompts.PROMPT_C, "critical_c", 0, config.BASELINE_TEMPERATURE)
