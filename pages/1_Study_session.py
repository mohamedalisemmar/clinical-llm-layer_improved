"""Participant study session: consent -> 2 blocks (LLM only / LLM + layer,
counterbalanced) -> SUS, NASA-TLX and trust after each block -> final questions.
Every answer is written to data/results/*.csv immediately."""
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from storage import (QUESTIONNAIRE_FIELDS, QUESTIONNAIRES_CSV, RESPONSE_FIELDS, RESPONSES_CSV,  # noqa: E402
                     SESSION_FIELDS, SESSIONS_CSV, append_row, load_cases, load_output, outputs_meta)
from ui.components import (inject_css, mock_warning, render_case, render_layer, render_raw,  # noqa: E402
                           render_verify_notice)
from ui.questionnaires import LIKERT_5, SUS_ITEMS, TLX_ITEMS, TRUST_ITEMS  # noqa: E402

st.set_page_config(page_title="Study session", layout="wide")
inject_css()

CASES = {c["id"]: c for c in load_cases()}
# Counterbalancing: condition order x case-set assignment (4 groups).
GROUPS = {
    1: [("A", 1), ("B", 2)],
    2: [("B", 1), ("A", 2)],
    3: [("A", 2), ("B", 1)],
    4: [("B", 2), ("A", 1)],
}
ss = st.session_state
ss.setdefault("stage", "setup")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def block_cases(case_set: int, pid: str, block: int) -> list[str]:
    ids = [cid for cid, c in CASES.items() if c["set"] == case_set]
    rng = random.Random(f"{pid}-{block}")
    rng.shuffle(ids)
    k = config.MAX_CASES_PER_BLOCK
    if k and k < len(ids):  # stratified: round-robin over categories so every type is included
        by_cat: dict[str, list[str]] = {}
        for cid in ids:
            by_cat.setdefault(CASES[cid]["category"], []).append(cid)
        chosen, cats = [], sorted(by_cat, key=lambda c: c != "seeded_error")
        while len(chosen) < k:
            for cat in cats:
                if by_cat[cat] and len(chosen) < k:
                    chosen.append(by_cat[cat].pop(0))
        rng.shuffle(chosen)
        ids = chosen
    return ids


def session_row(event: str, **extra) -> None:
    append_row(SESSIONS_CSV, {"timestamp": now(), "participant_id": ss.pid, "group": ss.group,
                              "event": event, **ss.profile, **extra}, SESSION_FIELDS)


# ---------------------------------------------------------------------------
if ss.stage == "setup":
    st.title("Study session")
    st.write("Researcher: fill this in, then hand the screen to the participant.")
    missing = [cid for cid in CASES if load_output(cid) is None]
    if missing:
        st.error(f"{len(missing)} case(s) have no precomputed AI output ({', '.join(missing[:6])}...). "
                 "Run `python -m scripts.precompute_outputs` first.")
        st.stop()
    mock_warning(outputs_meta())
    c1, c2 = st.columns(2)
    with c1:
        pid = st.text_input("Participant ID", placeholder="P01")
        group = st.selectbox("Counterbalancing group", [1, 2, 3, 4],
                             help="Rotate 1, 2, 3, 4 across participants so each order is used equally.")
        st.caption("Group 1: LLM only on set 1, then layer on set 2. Group 2: layer on set 1, then LLM only "
                   "on set 2. Groups 3 and 4 swap the case sets.")
    with c2:
        role = st.selectbox("Role", ["Practising physician", "Resident", "Nurse", "Medical student (pilot only)",
                                     "Other"])
        exp = st.number_input("Years of clinical experience", 0, 50, 0)
        specialty = st.text_input("Specialty")
        ai_fam = st.select_slider("Familiarity with AI tools",
                                  ["None", "A little", "Moderate", "High"], value="A little")
    if st.button("Start session", type="primary", disabled=not pid.strip()):
        ss.pid, ss.group = pid.strip(), group
        ss.profile = {"role": role, "experience_years": exp, "specialty": specialty, "ai_familiarity": ai_fam}
        ss.blocks = [(cond, block_cases(cset, ss.pid, i)) for i, (cond, cset) in enumerate(GROUPS[group])]
        ss.block, ss.idx = 0, 0
        ss.stage = "consent"
        st.rerun()

# ---------------------------------------------------------------------------
elif ss.stage == "consent":
    st.title("Information and consent")
    st.markdown("""
This study examines how clinicians read and assess answers produced by an AI system for clinical cases.

* All cases are **synthetic**. No real patient data are used.
* You will review a series of cases, each with an AI-generated answer, and decide whether you would accept it.
  **The AI can be wrong.** Judge each answer as you would a colleague's opinion.
* The session has two blocks and takes about 45 to 60 minutes. Short questionnaires follow each block.
* Participation is voluntary. You can stop at any time without giving a reason.
* Your answers are stored under a participant code only and used, anonymised, in an internship report.
""")
    agree = st.checkbox("I have read this information and agree to take part.")
    if st.button("Continue", type="primary", disabled=not agree):
        session_row("start", consent="yes")
        ss.stage = "instructions"
        st.rerun()

# ---------------------------------------------------------------------------
elif ss.stage == "instructions":
    cond, ids = ss.blocks[ss.block]
    st.title(f"Block {ss.block + 1} of 2")
    extra = ("The AI answer is displayed as structured information with a reliability indicator."
             if cond == "B" else "The AI answer is displayed as the AI wrote it.")
    st.markdown(f"""
You will see **{len(ids)} cases**. {extra}

For each case:
1. Read the patient information and the AI answer.
2. Decide whether you would **accept** or **reject** the AI's recommendation.
3. Answer the short questions below it.

Work at your normal pace. Time per case is recorded.
""")
    if st.button("Start block", type="primary"):
        ss.stage = "case"
        st.rerun()

# ---------------------------------------------------------------------------
elif ss.stage == "case":
    cond, ids = ss.blocks[ss.block]
    cid = ids[ss.idx]
    case, out = CASES[cid], load_output(cid)
    key = f"{ss.block}_{cid}"
    if ss.get("timer_key") != key:
        ss.timer_key, ss.t0 = key, time.time()

    st.progress((ss.idx) / len(ids), text=f"Block {ss.block + 1} of 2, case {ss.idx + 1} of {len(ids)}")
    left, right = st.columns([5, 6], gap="large")
    with left:
        st.subheader("Patient")
        render_case(case)
    with right:
        st.subheader("AI answer")
        if cond == "A":
            render_raw(out)
        else:
         # Theory: Condition B = Functions A–C + B indicator for the clinician.
         # Function D (judge) and full signal table stay in Layer explorer / logs only.
         render_layer(out, show_judge=False, show_signals=False)

    st.divider()
    st.subheader("Your assessment")
    q1, q2 = st.columns(2, gap="large")
    with q1:
        decision = st.radio("Would you accept the AI's recommendation?", ["Accept", "Reject"],
                            index=None, horizontal=True, key=f"dec_{key}")
        agreement = st.radio("Do you agree with the recommendation?",
                             ["Agree", "Partially agree", "Disagree", "Unclear"],
                             index=None, horizontal=True, key=f"agr_{key}")
        perceived = st.radio("How reliable do you judge this AI answer?", ["Low", "Moderate", "High"],
                             index=None, horizontal=True, key=f"per_{key}")
        indicator = None
        if cond == "B":
            indicator = st.radio("Was the displayed reliability indicator appropriate?",
                                 ["Too high", "Appropriate", "Too low"],
                                 index=None, horizontal=True, key=f"ind_{key}")
        verify_shown = cond == "B" and (out["reliability"]["level"] == "LOW" or agreement == "Disagree")
        if cond == "B" and agreement == "Disagree" and out["reliability"]["level"] != "LOW":
            render_verify_notice()
    with q2:
        usefulness = st.radio("How useful was the AI's explanation for your decision?",
                              ["1 Not useful", "2", "3", "4", "5 Very useful"],
                              index=None, horizontal=True, key=f"use_{key}")
        confidence = st.radio("How confident are you in your own decision?",
                              ["1 Not confident", "2", "3", "4", "5 Very confident"],
                              index=None, horizontal=True, key=f"conf_{key}")
        recall = st.text_input("In a few words, what was the main reason given for the recommendation?",
                               key=f"rec_{key}")
        missing_noted = st.text_input("Was any important information missing? (optional)", key=f"mis_{key}")
        own_dx = st.text_input("Your own most likely diagnosis (optional)", key=f"own_{key}")
        comments = st.text_area("Comments or corrections (optional)", key=f"com_{key}", height=80)

    required = [decision, agreement, perceived, usefulness, confidence] + ([indicator] if cond == "B" else [])
    ready = all(x is not None for x in required) and recall.strip()
    if st.button("Save and continue", type="primary", disabled=not ready):
        append_row(RESPONSES_CSV, {
            "timestamp": now(), "participant_id": ss.pid, "group": ss.group, "block": ss.block + 1,
            "condition": cond, "case_id": cid, "category": case["category"], "case_set": case["set"],
            "shown_diagnosis": out["structured"]["primary_diagnosis"],
            "layer_reliability": out["reliability"]["level"],
            "decision": decision.lower(), "agreement": agreement, "perceived_reliability": perceived,
            "indicator_appropriateness": indicator or "", "explanation_usefulness": usefulness[0],
            "decision_confidence": confidence[0], "main_factor_recall": recall.strip(),
            "missing_info_noted": missing_noted.strip(), "own_diagnosis": own_dx.strip(),
            "comments": comments.strip(), "time_seconds": round(time.time() - ss.t0, 1),
            "verify_prompt_shown": verify_shown,
        }, RESPONSE_FIELDS)
        if ss.idx + 1 < len(ids):
            ss.idx += 1
        else:
            ss.stage = "questionnaire"
        st.rerun()
    if not ready:
        st.caption("Answer every question without '(optional)' to continue.")

# ---------------------------------------------------------------------------
elif ss.stage == "questionnaire":
    cond, _ = ss.blocks[ss.block]
    st.title(f"About block {ss.block + 1}")
    st.write("These questions are about the display you just used.")
    answers = {}
    st.subheader("Usability")
    for i, item in enumerate(SUS_ITEMS, 1):
        answers[f"sus_{i}"] = st.radio(f"{i}. {item}", LIKERT_5, index=None, horizontal=True,
                                       key=f"sus{i}_{ss.block}")
    st.subheader("Workload")
    for k, name, question, lo, hi in TLX_ITEMS:
        answers[k] = st.slider(f"{name}: {question}", 0, 100, 50, 5, key=f"{k}_{ss.block}")
        st.caption(f"0 = {lo}, 100 = {hi}")
    st.subheader("Reliance")
    for i, item in enumerate(TRUST_ITEMS, 1):
        answers[f"trust_{i}"] = st.radio(item, LIKERT_5, index=None, horizontal=True, key=f"tr{i}_{ss.block}")

    ready = all(v is not None for v in answers.values())
    if st.button("Save questionnaire", type="primary", disabled=not ready):
        row = {k: (int(v[0]) if isinstance(v, str) else v) for k, v in answers.items()}
        append_row(QUESTIONNAIRES_CSV, {"timestamp": now(), "participant_id": ss.pid, "group": ss.group,
                                        "block": ss.block + 1, "condition": cond, **row}, QUESTIONNAIRE_FIELDS)
        if ss.block == 0:
            ss.block, ss.idx, ss.stage = 1, 0, "instructions"
        else:
            ss.stage = "final"
        st.rerun()

# ---------------------------------------------------------------------------
elif ss.stage == "final":
    st.title("Last questions")
    pref = st.radio("Which display did you prefer?",
                    ["The first block's display", "The second block's display", "No preference"], index=None)
    comments = st.text_area("Anything else you would like to tell us about the AI answers or the displays?")
    if st.button("Finish", type="primary", disabled=pref is None):
        order = [c for c, _ in ss.blocks]
        mapped = {"The first block's display": order[0], "The second block's display": order[1]}.get(pref, "none")
        session_row("finish", preferred_condition=mapped, final_comments=comments.strip())
        ss.stage = "done"
        st.rerun()

elif ss.stage == "done":
    st.title("Thank you")
    st.write("The session is complete and your answers have been saved.")
    if st.button("Start a new participant"):
        for k in list(ss.keys()):
            del ss[k]
        st.rerun()
