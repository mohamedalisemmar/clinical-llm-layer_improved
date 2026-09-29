"""Home page.  Run with:  streamlit run app.py"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from storage import RESPONSES_CSV, load_cases, load_output, outputs_meta  # noqa: E402
from ui.components import inject_css, mock_warning  # noqa: E402

st.set_page_config(page_title="Clinical LLM intermediary layer", layout="wide")
inject_css()

st.title("A lightweight intermediary layer between an LLM and the clinician")
st.write("Research prototype. It structures an LLM's clinical answer, builds a reliability signal from "
         "observable checks, shows a clinician-oriented rationale and records the clinician's judgment, "
         "without retrieval (RAG). All cases are synthetic.")

cases = load_cases()
ready = sum(load_output(c["id"]) is not None for c in cases)
n_resp = max(0, sum(1 for _ in open(RESPONSES_CSV, encoding="utf-8")) - 1) if RESPONSES_CSV.exists() else 0
meta = outputs_meta()

c1, c2, c3 = st.columns(3)
c1.metric("Cases with precomputed output", f"{ready} / {len(cases)}")
c2.metric("Outputs generated with", meta.get("provider", "not yet run"))
c3.metric("Case responses recorded", n_resp)
mock_warning(meta)

st.markdown(f"""
### Pages

**Study session** runs one participant through consent, two counterbalanced blocks
(LLM only, and LLM with the layer), the SUS, NASA-TLX and trust questionnaires, and final questions.

**Layer explorer** shows any case side by side in both conditions, lists every reliability signal,
and can run the layer live on a new case. Use it for demos to your supervisor.

**Results** compares the two conditions and checks whether the reliability indicator tracks correctness.

### Before running a study
1. Set your LLM in `.env` (current live provider: `{config.LLM_PROVIDER}`, model `{config.model_name()}`).
2. Run `python -m scripts.precompute_outputs` so every participant sees identical AI answers.
3. Review `data/outputs/adjudication.csv` and have a clinician check the cases.
""")
