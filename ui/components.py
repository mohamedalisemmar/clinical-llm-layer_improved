"""Shared Streamlit rendering: the patient case, Condition A (raw answer),
Condition B (the intermediary layer = Functions A-D), and the signal table."""
from __future__ import annotations

import html

import streamlit as st

from llm.prompts import CASE_FIELDS
from layer.inspectability import build_rationale
LEVEL_STYLE = {
    "HIGH": ("#1E6B52", "#E7F3EE", "High"),
    "MODERATE": ("#8A5300", "#FBF1E1", "Moderate"),
    "LOW": ("#A3231B", "#FBE9E7", "Low"),
}
STATUS_ICON = {"pass": "✓", "warn": "!", "fail": "✕", "na": "–"}
STATUS_COLOR = {"pass": "#1E6B52", "warn": "#8A5300", "fail": "#A3231B", "na": "#6B7680"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500&display=swap');
html, body, [class*="css"], .stMarkdown, .stRadio, .stTextInput, .stTextArea {
  font-family: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
h1, h2, h3 { font-family: 'IBM Plex Serif', Georgia, serif; font-weight: 500; letter-spacing: -0.01em; }
.block-container { max-width: 1180px; padding-top: 2rem; }
.case-sheet { border-left: 3px solid #2F5D8A; padding: 0.2rem 0 0.2rem 1.1rem; }
.case-sheet .who { font-size: 1.15rem; font-weight: 600; margin-bottom: 0.6rem; }
.case-row { display: grid; grid-template-columns: 9.5rem 1fr; gap: 0.8rem; padding: 0.35rem 0;
            border-bottom: 1px solid #E4E9ED; line-height: 1.5; }
.case-row .k { color: #56626D; font-size: 0.9rem; }
.case-row .v { font-size: 0.97rem; }
.case-row .v.absent { color: #8A949C; font-style: italic; }
.raw-answer { background: #F7F9FA; border: 1px solid #DDE3E8; border-radius: 6px; padding: 1.1rem 1.3rem;
              white-space: pre-wrap; line-height: 1.6; font-size: 0.97rem; }
.rec { font-size: 1.12rem; line-height: 1.5; margin: 0.2rem 0 0.9rem 0; }
.rec .dx { font-weight: 600; display: block; font-size: 1.25rem; margin-bottom: 0.2rem; }
.rel { border-radius: 6px; padding: 0.85rem 1.1rem; margin: 0 0 1.1rem 0; display: flex; gap: 1.1rem; align-items: baseline; }
.rel .lvl { font-weight: 600; font-size: 1.05rem; min-width: 6.5rem; }
.rel .why { font-size: 0.95rem; line-height: 1.45; }
.verify { border: 1.5px solid #A3231B; color: #A3231B; border-radius: 6px; padding: 0.6rem 1rem;
          margin-bottom: 1rem; font-weight: 500; }
.field h4 { font-family: 'IBM Plex Sans', sans-serif; font-size: 0.92rem; font-weight: 600; color: #34414D;
            margin: 0.4rem 0 0.3rem 0; }
.field ul { margin: 0 0 0.6rem 1.1rem; padding: 0; }
.field li { margin: 0.15rem 0; line-height: 1.45; font-size: 0.95rem; }
.crit { color: #A3231B; font-weight: 600; font-size: 0.8rem; margin-left: 0.35rem; }
.inconsistent { background: #FBF1E1; border-radius: 6px; padding: 0.6rem 1rem; margin-bottom: 0.8rem; font-size: 0.95rem; }
.sig { display: grid; grid-template-columns: 1.4rem 15rem 1fr; gap: 0.6rem; padding: 0.35rem 0;
       border-bottom: 1px solid #E4E9ED; font-size: 0.92rem; }
.sig .ic { font-weight: 700; text-align: center; }
.mockwarn { background: #FBF1E1; border-radius: 6px; padding: 0.5rem 0.9rem; font-size: 0.9rem; margin-bottom: 1rem; }
</style>
"""
_EMPTY_SAFE = ""  # inspectability uses "" for "no inconsistencies"

def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _e(text) -> str:
    return html.escape(str(text or ""))


def render_case(case: dict) -> None:
    p = case.get("patient", {})
    rows = [f'<div class="who">{_e(p.get("age"))}-year-old {_e(str(p.get("sex", "")).lower())}</div>']
    for key, label in CASE_FIELDS:
        val = (case.get(key) or "").strip()
        cls, shown = ("v", _e(val)) if val else ("v absent", "Not available")
        rows.append(f'<div class="case-row"><div class="k">{label}</div><div class="{cls}">{shown}</div></div>')
    st.markdown(f'<div class="case-sheet">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_raw(output: dict) -> None:
    """Condition A: the LLM answer exactly as generated."""
    st.markdown(f'<div class="raw-answer">{_e(output["raw_response"])}</div>', unsafe_allow_html=True)


def _list(title: str, items: list, empty: str = "None stated") -> str:
    lis = "".join(f"<li>{i}</li>" for i in items) if items else f"<li><em>{empty}</em></li>"
    return f'<div class="field"><h4>{title}</h4><ul>{lis}</ul></div>'


def render_reliability(rel: dict) -> None:
    color, bg, word = LEVEL_STYLE[rel["level"]]
    why = _e(rel["explanation"].split(":", 1)[-1].strip())
    st.markdown(
        f'<div class="rel" style="background:{bg};border-left:4px solid {color}">'
        f'<div class="lvl" style="color:{color}">Reliability: {word}</div><div class="why">{why}</div></div>',
        unsafe_allow_html=True)


def render_verify_notice() -> None:
    st.markdown('<div class="verify">Verify independently before acting on this recommendation.</div>',
                unsafe_allow_html=True)


def render_layer(output: dict, *, show_judge: bool = True, show_signals: bool = True) -> None:
    """Condition B: Function A fields via Function C layout + Function B indicator.

    show_signals / show_judge: keep True in Layer explorer (research/debug).
    Study session should pass False so the UI stays lightweight and Function D
    stays supplementary (theoretical model).
    """
    rel = output["reliability"]
    c = build_rationale(output["structured"])

    st.markdown(
        f'<div class="rec"><span class="dx">{_e(c.primary_diagnosis)}</span>'
        f'{_e(c.recommendation)}</div>',
        unsafe_allow_html=True,
    )
    render_reliability(rel)
    if rel.get("verify_independently"):
        render_verify_notice()

    # Only real conflicts (empty placeholder from build_rationale is "")
    inconsistencies = [x for x in c.input_inconsistencies if x and x != _EMPTY_SAFE]
    if inconsistencies:
        st.markdown(
            '<div class="inconsistent"><strong>The case record contains conflicting information:</strong> '
            + _e("; ".join(inconsistencies))
            + "</div>",
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(_list("Main factors considered", [_e(x) for x in c.main_factors]), unsafe_allow_html=True)
        st.markdown(_list("Alternative possibilities", [_e(x) for x in c.alternatives]), unsafe_allow_html=True)
        st.markdown(_list("Limitations", [_e(x) for x in c.limitations]), unsafe_allow_html=True)
    with col2:
        st.markdown(_list("Missing information", [_e(x) for x in c.missing_information]), unsafe_allow_html=True)
        st.markdown(
            _list("What would change this recommendation", [_e(x) for x in c.what_would_change]),
            unsafe_allow_html=True,
        )
        st.markdown(
            _list("Verify before acting", [_e(x) for x in c.verification_points]),
            unsafe_allow_html=True,
        )

    if show_signals:
        st.markdown("##### Reliability signals (research detail)")
        render_signals(output.get("signals") or [])

    if show_judge and output.get("judge") and output["judge"].get("available", True):
        j = output["judge"]
        st.markdown("##### Automated quality check (supplementary — not the reliability level)")
        # keep your existing judge rendering block below this line unchanged
        if j.get("summary"):
            st.caption(_e(j["summary"]))
        scores = j.get("scores") or {}
        if scores:
            st.write({k: scores[k] for k in scores})
        if j.get("safety_concern"):
            st.warning(_e(j.get("safety_note") or "Safety concern flagged by automated check."))
def render_signals(signals: list) -> None:
  
    rows = []
    for sig in signals:
        ic, col = STATUS_ICON[sig["status"]], STATUS_COLOR[sig["status"]]
        rows.append(f'<div class="sig"><div class="ic" style="color:{col}">{ic}</div>'
                    f'<div>{_e(sig["label"])}</div><div>{_e(sig["detail"])}</div></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)
    st.caption("The level is set by rules, not by a score: a failed consistency check or a contradiction "
               "gives Low; High needs every core check to pass with nothing missing; everything else is Moderate.")

def mock_warning(meta: dict) -> None:
    if meta.get("provider") == "mock":
        st.markdown('<div class="mockwarn">These outputs were produced by the offline <strong>mock</strong> '
                    "simulator. Use them to test the workflow only. Run "
                    "<code>python -m scripts.precompute_outputs --force</code> with a real LLM before the study.</div>",
                    unsafe_allow_html=True)
