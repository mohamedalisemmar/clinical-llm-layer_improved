"""Results dashboard: runs the same analysis as `python -m evaluation.analysis`."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.analysis import run_analysis  # noqa: E402
from storage import outputs_meta  # noqa: E402
from ui.components import inject_css, mock_warning  # noqa: E402

st.set_page_config(page_title="Results", layout="wide")
inject_css()
st.title("Results")
mock_warning(outputs_meta())

res = run_analysis(save=True)

st.subheader("Does the reliability indicator track correctness?")
st.write("Computed from the precomputed outputs and the adjudicated correctness. No participants needed.")
if res["layer_calibration"] is not None:
    st.dataframe(res["layer_calibration"])
    for line in res["layer_summary"]:
        st.write(line)
if "reliability_vs_correctness" in res["figures"]:
    st.pyplot(res["figures"]["reliability_vs_correctness"])

if res["n_responses"] == 0:
    st.info("No participant responses yet. Complete a session on the Study session page, "
            "and the comparison of the two conditions will appear here.")
    st.stop()

st.subheader(f"LLM only vs LLM + layer ({res['n_participants']} participants, {res['n_responses']} case responses)")
st.dataframe(res["main_table"])
for note in res["notes"]:
    st.caption(note)

cols = st.columns(2)
for i, name in enumerate(["reliance_by_condition", "time_by_condition", "questionnaires_by_condition",
                          "acceptance_by_category"]):
    if name in res["figures"]:
        with cols[i % 2]:
            st.pyplot(res["figures"][name])

st.subheader("By case category")
st.dataframe(res["by_category"])

if res["stats"] is not None:
    st.subheader("Paired statistical tests (per participant)")
    st.dataframe(res["stats"])

if res["judge_agreement"]:
    st.subheader("Automated judge vs clinicians")
    for line in res["judge_agreement"]:
        st.write(line)

st.caption("Tables and figures were also written to the results/ folder for the report.")
