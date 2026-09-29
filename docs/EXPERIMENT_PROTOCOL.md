# Experiment protocol

## Design
Within-subject, two conditions, counterbalanced.

| Group | Block 1 | Block 2 |
|---|---|---|
| 1 | Condition A (LLM only), case set 1 | Condition B (LLM + layer), case set 2 |
| 2 | Condition B, case set 1 | Condition A, case set 2 |
| 3 | Condition A, case set 2 | Condition B, case set 1 |
| 4 | Condition B, case set 2 | Condition A, case set 1 |

Assign participants to groups in rotation (P01 → 1, P02 → 2, P03 → 3, P04 → 4, P05 → 1...).
Two case sets are used because showing the same case twice would let participants remember their first
answer. Both sets have the same mix of categories. Case order within a block is randomised per participant.

## Participants
* Target: 8 to 12 practising physicians or residents (the more, the better; the statistical tests need at
  least 5 who complete both blocks).
* A pilot with 1 or 2 medical students is used only to test the wording and timing. Pilot data are
  excluded from the analysis (use IDs such as `PILOT1` and delete their rows).

## Before the first session
- [ ] Supervisor approves the clinical task, cases and participant type.
- [ ] A clinician has reviewed `docs/case_review_sheet.csv`; cases corrected in `data/cases.json`.
- [ ] Ethics approval or exemption obtained if the host institution requires it.
- [ ] Real LLM outputs precomputed (`python -m scripts.precompute_outputs --force`); model name recorded.
- [ ] `data/outputs/adjudication.csv` reviewed: every `output_correct` value checked by hand.
- [ ] Layer calibration checked on the Results page (does LOW catch the seeded errors?).
- [ ] Pilot session run; timing acceptable (adjust `MAX_CASES_PER_BLOCK` if needed).
- [ ] `data/results/` emptied of pilot data.

## Session script (about 45 to 60 minutes)
1. Welcome. Explain the study in two sentences. Do **not** say which display is expected to be better.
2. Researcher fills in the setup screen (ID, group, role, experience).
3. Participant reads the information screen and gives consent.
4. Block 1: cases, then SUS, NASA-TLX and trust items.
5. Block 2: cases, then the same questionnaires.
6. Final questions (preference, comments). Optional 5-minute debrief interview; take notes.
7. Tell the participant which answers were deliberately wrong, if they ask.

Do not help the participant during the cases. If they ask whether the AI is right, answer:
"Please decide as you would in practice."

## What is recorded
* `data/results/responses.csv`: one row per case (decision, agreement, perceived reliability, indicator
  rating, usefulness, confidence, free-text recall, time in seconds, whether a verify prompt appeared)
* `data/results/questionnaires.csv`: SUS items, NASA-TLX subscales, trust items per block
* `data/results/sessions.csv`: participant profile, consent, preference, final comments

## Measures and hypotheses
| Hypothesis | Measure | Expected if the layer helps |
|---|---|---|
| H1 The layer improves detection of wrong AI answers | Error detection on seeded errors | B > A |
| H2 It does not reduce acceptance of correct answers | Correct acceptance | B ≈ A |
| H3 It improves calibrated reliance | Appropriate reliance, perceived-reliability discrimination | B > A |
| H4 It improves comprehension | Explanation usefulness, recall accuracy (coded) | B > A |
| H5 Its usability cost is acceptable | Time per case, SUS, NASA-TLX | small or no difference |
| H6 The indicator tracks correctness | LOW on incorrect vs correct outputs | LOW mostly on incorrect |

## Coding the free-text recall (comprehension)
After the study, add a column `recall_correct` (0/1) to `responses.csv`: 1 if the participant's
"main reason" matches one of the case's `key_findings` or the reasons the AI gave. Have a second person code
a subset to report agreement.
