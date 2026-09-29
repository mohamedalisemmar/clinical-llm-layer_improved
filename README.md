# Clinical LLM intermediary layer: research prototype

Practical implementation of the design in **Chapter 1 (Theoretical Study)**: a lightweight layer between an
LLM's output and the clinician that **structures** the output, builds a **reliability signal** from observable
checks, shows a **clinician-oriented rationale**, and **captures clinician judgment**, without RAG.
It includes the experiment that compares **Condition A (LLM only)** with **Condition B (LLM + layer)**.

All clinical cases are synthetic. This is a research prototype, not a clinical tool.

---

## 1. What is in the folder

```
clinical_llm_layer/
├── app.py                        Home page (streamlit run app.py)
├── pages/
│   ├── 1_Study_session.py        Participant session: consent, 2 blocks, questionnaires   (Function E)
│   ├── 2_Layer_explorer.py       Side-by-side A vs B, every signal, live runs (supervisor demo)
│   └── 3_Results.py              Results dashboard
├── layer/                        THE INTERMEDIARY LAYER
│   ├── pipeline.py               Runs everything in order
│   ├── generation.py             Prompt A (shown answer), Prompt B (repeated), Prompt C (critical)
│   ├── structuring.py            Function A: raw text -> fixed fields
│   ├── equivalence.py            Diagnoses compared by meaning, not wording
│   ├── consistency.py            Signals: repeated-generation consistency, prompt agreement
│   ├── contradiction.py          Signal: contradictions (rules + LLM check)
│   ├── completeness.py           Signal: structural completeness
│   ├── missing_info.py           Signals: missing info, conflicting case data, stated confidence
│   ├── reliability.py            Function B: LOW / MODERATE / HIGH rule + explanation
│   ├── judge.py                  Function D: LLM-as-a-Judge (supplementary only)
│   └── schemas.py                Pydantic data structures
├── llm/
│   ├── client.py                 Anthropic, any OpenAI-compatible API (OpenAI, Groq, Ollama...), or mock
│   ├── prompts.py                Every prompt in one file
│   ├── mock.py                   Offline simulator for testing without an API key
│   └── json_utils.py
├── evaluation/
│   ├── analysis.py               All metrics, tables, figures, statistical tests
│   ├── metrics.py                SUS, NASA-TLX, error detection, appropriate reliance...
│   └── grading.py                Auto-grades each AI answer against ground truth
├── scripts/
│   ├── precompute_outputs.py     Runs the LLM + layer once per case (do this before the study)
│   ├── test_llm_connection.py    Checks your API setup
│   └── export_case_review.py     Spreadsheet for a clinician to validate the cases
├── data/
│   ├── cases.json                30 synthetic cases with ground truth
│   ├── outputs/                  Cached AI outputs per case + adjudication.csv
│   └── results/                  Participant data (responses, questionnaires, sessions)
├── results/                      Tables and figures for the report (generated)
├── docs/                         Protocol, consent form, chapter-writing guide, case review sheet
└── tests/                        pytest tests (rule, pipeline, analysis)
```

The folder ships with **mock outputs already computed**, so the app works immediately. They are labelled as
mock everywhere and must be replaced with real LLM outputs before the study.

## 2. Install and run (5 minutes)

```bash
cd clinical_llm_layer
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
streamlit run app.py
```

Open the **Layer explorer** page first: pick case `E01` and switch between the tabs to see the whole idea.

Run the tests with `python -m pytest -q`.

## 3. Connect a real LLM

Edit `.env`. Three options:

| Option | `.env` settings | Cost |
|---|---|---|
| Claude | `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=...` | Paid, cheap with Haiku |
| OpenAI / Groq / OpenRouter | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=...`, `OPENAI_BASE_URL=...` (not needed for OpenAI) | Groq has a free tier |
| Ollama (local) | `LLM_PROVIDER=openai`, `OPENAI_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=llama3.1:8b` | Free |

Then:

```bash
python -m scripts.test_llm_connection      # should print a reply
python -m scripts.precompute_outputs --force
```

One case costs about 10 LLM calls (1 answer, 1 structuring, 5 repeated, 1 critical, 1–2 equivalence,
1 contradiction, 1 judge), so about 300 calls for the whole set. Pick one model and do not change it
during the study, and write the model name in the report.

## 4. How the layer works

```
case ─► Prompt A ─► raw answer ──────────────────────────────────► Condition A (shown as-is)
                        │
                        ├─► Function A  structure into fields (recommendation kept exactly as written)
                        ├─► Function B  Prompt B x5 ─► consistency
                        │               Prompt C    ─► prompt agreement
                        │               contradiction, completeness, missing info,
                        │               conflicting case data, stated confidence
                        │               └─► rule ─► LOW / MODERATE / HIGH + reason
                        ├─► Function C  rationale fields, "what would change this"
                        └─► Function D  LLM-as-a-Judge (shown separately, not in the rule)
                                                                 └────► Condition B
clinician ─► Function E  accept/reject, agreement, reliability rating, comments ─► CSV audit trail
```

**The reliability rule** (`layer/reliability.py`, exactly as in Chapter 1, Section 3.4.2):

* **LOW** if the repeated answers do not reproduce the diagnosis (fewer than 3 of 5 agree) **or** a clear
  contradiction is found. Either alone is enough. Low also triggers "Verify independently".
* **HIGH** only if consistency passes, the alternative prompts agree, there is no contradiction, all fields
  are filled, and nothing caps it (no critical missing information, no conflicting case data, the model
  does not itself state low confidence).
* **MODERATE** in every other case, including "stable but incomplete".
* No number or percentage is ever shown. Stated confidence can only lower the level, never raise it.

**Fair comparison:** the clinician sees the same recommendation in both conditions. The layer changes only
how it is presented and what extra information comes with it.

**Seeded errors:** for the 6 `seeded_error` cases, the answer shown is a deliberately wrong, fluent answer
stored in `cases.json`, as the chapter requires (Section 4.2). The layer still runs its checks on it.

## 5. The cases (`data/cases.json`)

| Category | Count | Purpose |
|---|---|---|
| straightforward | 10 | Clear answer, should be accepted |
| ambiguous | 6 | Several plausible answers, tests uncertainty display |
| missing_information | 5 | Key data withheld (ECG, pregnancy test...) |
| contradictory_input | 3 | The case record contradicts itself |
| seeded_error | 6 | Confidently wrong AI answer, should be rejected |

Cases are split into two balanced sets of 15 (set 1 and set 2), so a participant never sees the same case twice.
**Have a clinician review them before the study:** run `python -m scripts.export_case_review` and send
`docs/case_review_sheet.csv`.

## 6. Running the study

See `docs/EXPERIMENT_PROTOCOL.md`. In short:

1. Real outputs precomputed; `data/outputs/adjudication.csv` reviewed (column `output_correct`, set
   `adjudicated_by` to your name for rows you checked; your edits survive re-running precompute).
2. For each participant, open **Study session**, enter the ID and rotate groups 1 → 2 → 3 → 4.
3. After the sessions: `python -m evaluation.analysis`, or open the **Results** page.

For a shorter session, set `MAX_CASES_PER_BLOCK=8` in `.env`. Every category, including seeded errors,
is still included.

## 7. What the analysis produces

`results/results_table.csv|md` and `results/figures/*.png`:

* error detection (reject | incorrect), commission errors (accept | incorrect, the automation-bias measure),
  correct acceptance, appropriate reliance
* perceived-reliability discrimination, explanation usefulness, decision confidence, time per case
* SUS, raw NASA-TLX, trust items
* acceptance by case category
* Wilcoxon signed-rank tests per participant (when 5 or more participants completed both conditions)
* **layer calibration**: does LOW / MODERATE / HIGH track actual correctness? (needs no participants)
* agreement between the LLM judge and clinicians

The key point for the report: **success is not higher acceptance.** It is more rejections of wrong answers
without losing correct acceptances, and without a large cost in time or workload. A null or negative
result is a valid finding.

## 8. Mapping to Chapter 1

See `docs/PRACTICAL_CHAPTER_GUIDE.md` for the full concept → code → measure table and an outline for
the practical chapter.
