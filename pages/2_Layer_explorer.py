"""Researcher / demo view: compare Condition A and Condition B for any case,
inspect every signal, or run the layer live on a new case."""
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from layer.pipeline import run_layer  # noqa: E402
from llm.client import LLMError, get_client  # noqa: E402
from storage import load_cases, load_output, outputs_meta  # noqa: E402
from ui.components import inject_css, mock_warning, render_case, render_layer, render_raw, render_signals  # noqa: E402

st.set_page_config(page_title="Layer explorer", layout="wide")
inject_css()
st.title("Layer explorer")
st.write("Compare what the clinician sees with and without the intermediary layer, and inspect every signal.")

cases = load_cases()
source = st.radio("Case source", ["Study case (precomputed)", "Study case (run live)", "New case (run live)"],
                  horizontal=True)

case, output = None, None
if source.startswith("Study case"):
    labels = {f'{c["id"]}  {c["title"]}  ({c["category"].replace("_", " ")})': c for c in cases}
    case = labels[st.selectbox("Case", list(labels))]
    if source.endswith("(precomputed)"):
        output = load_output(case["id"])
        mock_warning(outputs_meta())
        if output is None:
            st.info("No precomputed output for this case yet. Run `python -m scripts.precompute_outputs`, "
                    "or choose 'run live'.")
else:
    with st.form("custom"):
        c1, c2 = st.columns([1, 3])
        age = c1.number_input("Age", 0, 110, 50)
        sex = c1.selectbox("Sex", ["Male", "Female"])
        complaint = c2.text_area("Presenting complaint", height=70)
        history = st.text_area("History", height=70)
        meds = st.text_input("Medications")
        vitals = st.text_input("Vital signs")
        exam = st.text_area("Examination", height=70)
        inv = st.text_area("Investigations", height=70)
        submitted = st.form_submit_button("Use this case")
    if submitted or st.session_state.get("custom_case"):
        if submitted:
            st.session_state.custom_case = {
                "id": "custom", "patient": {"age": age, "sex": sex}, "presenting_complaint": complaint,
                "history": history, "medications": meds, "vitals": vitals, "examination": exam,
                "investigations": inv}
        case = st.session_state.custom_case

if case is not None and source.endswith("(run live)"):
    st.caption(f"Live provider: {config.LLM_PROVIDER} ({config.model_name()}). "
               f"About {config.N_SAMPLES + 5} LLM calls per case.")
    inject = st.checkbox("Use the seeded (deliberately wrong) answer if the case has one", value=True) \
        if case.get("injected_response") else False
    if st.button("Run the layer", type="primary"):
        try:
            client = get_client()
            with st.status("Running the intermediary layer", expanded=True) as status:
                output = run_layer(case, client, use_injected=inject, progress=st.write).model_dump()
                status.update(label=f"Done ({output['n_llm_calls']} LLM calls)", state="complete")
            st.session_state.live_output = output
        except LLMError as err:
            st.error(str(err))
    output = output or (st.session_state.get("live_output")
                        if st.session_state.get("live_output", {}).get("case_id") == case.get("id") else None)

if case is not None:
    st.divider()
    left, right = st.columns([5, 7], gap="large")
    with left:
        st.subheader("Patient")
        render_case(case)
        if case.get("reference_diagnosis"):
            with st.expander("Ground truth (researcher only)"):
                st.write(f"**Reference:** {case['reference_diagnosis']}")
                st.write(f"**Category:** {case['category'].replace('_', ' ')}")
                if case.get("notes_for_researcher"):
                    st.write(case["notes_for_researcher"])
    with right:
        if output:
            tab_a, tab_b, tab_s = st.tabs(["Condition A: LLM only", "Condition B: LLM + layer", "All signals"])
            with tab_a:
                render_raw(output)
            with tab_b:
                render_layer(output)
            with tab_s:

                render_signals(output.get("signals") or [])
                st.markdown("**Repeated answers (Prompt B)**")
                for i, (smp, same) in enumerate(zip(output["samples"], output["sample_agreement"]), 1):
                    st.write(f"{i}. {smp['primary_diagnosis'] or '(unparseable)'} "
                             f"{'(same as shown)' if same else '(different)'}")
                if output.get("critical"):
                    st.markdown(f"**Critical prompt (Prompt C):** {output['critical']['primary_diagnosis']}")
                st.download_button("Download full output (JSON)", json.dumps(output, indent=2, ensure_ascii=False),
                                   file_name=f"layer_output_{output['case_id']}.json")
