# From Chapter 1 to the practical chapter

## Concept → implementation → measure

| Chapter 1 concept | Where it is implemented | How it is measured |
|---|---|---|
| Ungrounded LLM output (Sec. 1.2.3) | `layer/generation.py` Prompt A; no retrieval anywhere | Condition A baseline |
| Lightweight intermediary layer (Sec. 3.4) | `layer/pipeline.py` | Condition B vs A |
| Function A, output structuring | `layer/structuring.py`, `llm/prompts.py` (PROMPT_STRUCTURE) | Explanation usefulness, recall |
| Prompt strategies A / B / C (Sec. 3.4.1) | `llm/prompts.py` | Prompt-agreement signal |
| Consistency across repeated generations | `layer/generation.py` + `layer/consistency.py` | Layer calibration table |
| Semantic-equivalence clustering [38, 39] | `layer/equivalence.py` | Same |
| Contradiction detection | `layer/contradiction.py` | Seeded contradictions, calibration |
| Missing-information awareness | `layer/missing_info.py` | `missing_information` cases |
| Structural completeness | `layer/completeness.py` | Same |
| Verbalised confidence, never alone [40] | `layer/missing_info.py`, can only lower the level | Same |
| Coarse rule-based indicator (Sec. 3.4.2) | `layer/reliability.py` | Indicator vs correctness; clinician "indicator appropriate?" |
| Function C, clinician rationale, no raw chain-of-thought | `ui/components.py` `render_layer` | Recall task, usefulness rating |
| "What would change this recommendation" probe | Structured field `what_would_change` | Usefulness, comments |
| Function D, LLM-as-a-Judge, supplementary [41] | `layer/judge.py` (not in the rule) | Judge vs clinician correlation |
| Function E, clinician feedback and audit trail | `pages/1_Study_session.py` → `data/results/*.csv` | All clinician measures |
| "Verify independently" prompt | Shown on LOW or on clinician disagreement | `verify_prompt_shown` column |
| Automation bias, commission errors [34] | Seeded-error cases | Commission-error rate |
| Trust calibration (Sec. 4.1) | Accept/reject split by correctness | Appropriate reliance, discrimination |
| Usability, ISO 9241-11 (Sec. 4.4) | Timer, SUS | Time per case, SUS |
| Cognitive workload | NASA-TLX after each block | Raw TLX |
| Five Rights, "lightweight" (Sec. 2.6) | Fixed layout, details in expanders | Time and TLX must not rise much |
| BLEU/ROUGE bounded role (Sec. 5.2) | Deliberately not used as primary | Stated in the report |
| Participants and ethics (Sec. 6.1) | `docs/EXPERIMENT_PROTOCOL.md`, `docs/CONSENT_FORM.md` | Consent logged |

## Suggested outline for Chapter 2 (Design and implementation) and Chapter 3 (Evaluation)

**Chapter 2: Design and implementation**
1. Clinical task and scope (differential diagnosis on synthetic adult cases; why; limits).
2. System architecture (the pipeline figure; the five functions).
3. LLM and prompts (model name and version, temperatures, the three prompts; include them in an appendix).
4. The intermediary layer, one section per function, each ending with "how this answers Section X of Chapter 1".
5. The reliability rule (the rule, its rationale, a worked example for a HIGH, a MODERATE and a LOW case;
   take them from the Layer explorer).
6. The clinician interface (screenshots of Condition A and Condition B side by side).
7. The case set (categories, construction, clinician review, seeded errors).
8. Implementation (stack: Python, Streamlit, Pydantic, pandas; testing; limitations of the mock).

**Chapter 3: Evaluation**
1. Protocol (design, groups, participants, ethics).
2. Automated evaluation of the indicator (calibration table and figure; false alarms and misses).
3. Clinician study results (main table; reliance figure; category figure; paired tests).
4. Usability cost (time, SUS, TLX).
5. Judge vs clinicians.
6. Qualitative feedback (comments, debrief).
7. Discussion: which functions helped, which did not, threats to validity (small n, synthetic cases,
   single model, single site), what grounding would add.

## Figures produced for you
* `results/figures/reliability_vs_correctness.png`
* `results/figures/reliance_by_condition.png`
* `results/figures/acceptance_by_category.png`
* `results/figures/time_by_condition.png`
* `results/figures/questionnaires_by_condition.png`

## Honest reporting reminders
* Report the model name, date, and that cases were synthetic.
* Report the indicator's misses (incorrect answers rated HIGH) and false alarms (correct answers rated LOW).
* Never report numbers produced with the mock provider.
* If the layer does not improve error detection, or increases time or workload, report it. It answers
  the research question just as much as a positive result.
