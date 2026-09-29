"""Analysis of the study: LLM only (A) vs LLM + layer (B).

Run:  python -m evaluation.analysis
Writes tables to results/ and figures to results/figures/.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from evaluation.metrics import (AGREEMENT, perceived_discrimination, reliance_metrics,  # noqa: E402
                                sus_score, tlx_raw)
from storage import QUESTIONNAIRES_CSV, RESPONSES_CSV, outputs_meta  # noqa: E402

COND_NAME = {"A": "LLM only", "B": "LLM + layer"}
COLORS = {"A": "#8A949C", "B": "#2F5D8A"}
LEVEL_ORDER = ["LOW", "MODERATE", "HIGH"]
TLX_COLS = ["tlx_mental", "tlx_physical", "tlx_temporal", "tlx_performance", "tlx_effort", "tlx_frustration"]

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def load_adjudication() -> pd.DataFrame:
    adj = _read(config.ADJUDICATION_PATH)
    if not adj.empty:
        adj["output_correct"] = adj["output_correct"].astype(str).str.lower().isin(["true", "1", "yes"])
    return adj


# ---------------------------------------------------------------------------
def layer_calibration(adj: pd.DataFrame):
    """Automated evaluation: does the indicator separate correct from incorrect outputs?"""
    if adj.empty:
        return None, [], None
    tab = pd.crosstab(adj["layer_reliability"], adj["output_correct"].map({True: "correct", False: "incorrect"}))
    tab = tab.reindex(index=[lvl for lvl in LEVEL_ORDER if lvl in tab.index])
    for col in ("correct", "incorrect"):
        if col not in tab:
            tab[col] = 0
    tab = tab[["correct", "incorrect"]]
    tab["share_incorrect"] = (tab["incorrect"] / tab.sum(axis=1)).round(2)

    inc, cor = adj[~adj["output_correct"]], adj[adj["output_correct"]]
    lines = []
    if len(inc):
        lines.append(f"Incorrect outputs flagged LOW: {(inc['layer_reliability'] == 'LOW').sum()} of {len(inc)} "
                     f"({(inc['layer_reliability'] == 'LOW').mean():.0%}).")
        lines.append(f"Incorrect outputs rated HIGH (missed): {(inc['layer_reliability'] == 'HIGH').sum()} of {len(inc)}.")
    if len(cor):
        lines.append(f"Correct outputs rated HIGH: {(cor['layer_reliability'] == 'HIGH').sum()} of {len(cor)}; "
                     f"rated LOW (false alarm): {(cor['layer_reliability'] == 'LOW').sum()} of {len(cor)}.")

    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    x = np.arange(len(tab))
    ax.bar(x - 0.18, tab["correct"], 0.36, label="Correct output", color="#1E6B52")
    ax.bar(x + 0.18, tab["incorrect"], 0.36, label="Incorrect output", color="#A3231B")
    ax.set_xticks(x, [lvl.capitalize() for lvl in tab.index])
    ax.set_ylabel("Number of cases")
    ax.set_title("Reliability indicator vs actual correctness")
    ax.legend(frameon=False)
    fig.tight_layout()
    return tab, lines, fig


# ---------------------------------------------------------------------------
def main_comparison(resp: pd.DataFrame, quest: pd.DataFrame):
    rows, notes = {}, []
    for cond in ("A", "B"):
        d = resp[resp["condition"] == cond]
        if d.empty:
            continue
        m = reliance_metrics(d)
        q = quest[quest["condition"] == cond] if not quest.empty else pd.DataFrame()
        rows[COND_NAME[cond]] = {
            "Case responses": m["n"],
            "Error detection (reject | incorrect)": m["error_detection"],
            "Commission errors (accept | incorrect)": m["commission_errors"],
            "Correct acceptance (accept | correct)": m["correct_acceptance"],
            "Appropriate reliance (overall)": m["appropriate_reliance"],
            "Perceived-reliability discrimination": perceived_discrimination(d),
            "Explanation usefulness (1-5)": pd.to_numeric(d["explanation_usefulness"]).mean(),
            "Decision confidence (1-5)": pd.to_numeric(d["decision_confidence"]).mean(),
            "Median time per case (s)": pd.to_numeric(d["time_seconds"]).median(),
            "SUS (0-100)": q["sus"].mean() if "sus" in q else np.nan,
            "NASA-TLX raw (0-100, lower better)": q["tlx"].mean() if "tlx" in q else np.nan,
            "Trust items (1-5)": q["trust"].mean() if "trust" in q else np.nan,
        }
    table = pd.DataFrame(rows).round(3)
    b = resp[resp["condition"] == "B"]
    if not b.empty:
        ind = b["indicator_appropriateness"].value_counts(normalize=True).round(2).to_dict()
        notes.append("Condition B, was the reliability indicator appropriate? "
                     + ", ".join(f"{k}: {v:.0%}" for k, v in ind.items()))
    notes.append("Success is NOT higher acceptance. It is higher error detection and appropriate reliance "
                 "without a large increase in time or workload.")
    return table, notes


def by_category(resp: pd.DataFrame) -> pd.DataFrame:
    g = resp.assign(accepted=resp["decision"].eq("accept"))
    t = g.pivot_table(index="category", columns="condition", values="accepted", aggfunc="mean")
    return t.rename(columns=COND_NAME).round(2).rename_axis(None, axis=1).add_prefix("Acceptance rate: ")


def paired_tests(resp: pd.DataFrame, quest: pd.DataFrame):
    per = []
    for (pid, cond), d in resp.groupby(["participant_id", "condition"]):
        m = reliance_metrics(d)
        per.append({"participant_id": pid, "condition": cond, "appropriate_reliance": m["appropriate_reliance"],
                    "error_detection": m["error_detection"],
                    "time": pd.to_numeric(d["time_seconds"]).median()})
    per = pd.DataFrame(per)
    if not quest.empty:
        per = per.merge(quest[["participant_id", "condition", "sus", "tlx"]], on=["participant_id", "condition"],
                        how="left")
    wide = per.pivot(index="participant_id", columns="condition")
    out = []
    for metric in ["appropriate_reliance", "error_detection", "time", "sus", "tlx"]:
        if metric not in per:
            continue
        try:
            pair = wide[metric][["A", "B"]].dropna()
        except KeyError:
            continue
        n = len(pair)
        row = {"metric": metric, "n_pairs": n, "mean_A": pair["A"].mean(), "mean_B": pair["B"].mean()}
        if n >= 5 and not (pair["A"] - pair["B"]).eq(0).all():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                w = stats.wilcoxon(pair["A"], pair["B"])
            row.update({"test": "Wilcoxon signed-rank", "statistic": w.statistic, "p_value": w.pvalue})
        else:
            row.update({"test": "not run (needs 5+ paired participants with differences)"})
        out.append(row)
    return pd.DataFrame(out).round(4) if out else None


def judge_vs_clinicians(resp: pd.DataFrame, adj: pd.DataFrame) -> list[str]:
    import json
    scores = {}
    for cid in resp["case_id"].unique():
        p = config.OUTPUTS_DIR / f"{cid}.json"
        if p.exists():
            j = json.loads(p.read_text(encoding="utf-8")).get("judge") or {}
            if j.get("overall") is not None:
                scores[cid] = j["overall"]
    if len(scores) < 5:
        return []
    agree = resp.assign(a=resp["agreement"].map(AGREEMENT)).groupby("case_id")["a"].mean()
    df = pd.DataFrame({"judge": pd.Series(scores), "clinician_agreement": agree}).dropna()
    lines = []
    if len(df) >= 5 and df["judge"].nunique() > 1 and df["clinician_agreement"].nunique() > 1:
        rho, p = stats.spearmanr(df["judge"], df["clinician_agreement"])
        lines.append(f"Spearman correlation, judge overall score vs mean clinician agreement: "
                     f"rho = {rho:.2f}, p = {p:.3f}, n = {len(df)} cases.")
    if not adj.empty:
        a = adj.set_index("case_id")["output_correct"]
        df2 = pd.DataFrame({"judge": pd.Series(scores), "correct": a}).dropna()
        if df2["correct"].nunique() == 2:
            lines.append(f"Mean judge score on correct outputs {df2[df2.correct]['judge'].mean():.2f} vs "
                         f"incorrect outputs {df2[~df2.correct.astype(bool)]['judge'].mean():.2f}.")
    return lines


# ---------------------------------------------------------------------------
def _figures(resp: pd.DataFrame, quest: pd.DataFrame, table: pd.DataFrame) -> dict:
    figs = {}
    conds = [c for c in ("A", "B") if c in resp["condition"].unique()]

    metrics = ["Error detection (reject | incorrect)", "Correct acceptance (accept | correct)",
               "Appropriate reliance (overall)"]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    x = np.arange(len(metrics))
    for i, c in enumerate(conds):
        vals = [table.loc[m, COND_NAME[c]] for m in metrics]
        ax.bar(x + (i - 0.5) * 0.36, vals, 0.36, label=COND_NAME[c], color=COLORS[c])
    ax.set_xticks(x, ["Error detection", "Correct acceptance", "Appropriate reliance"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Proportion")
    ax.set_title("Reliance on the AI by condition")
    ax.legend(frameon=False)
    fig.tight_layout()
    figs["reliance_by_condition"] = fig

    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    data = [pd.to_numeric(resp[resp.condition == c]["time_seconds"]) for c in conds]
    ax.boxplot(data, tick_labels=[COND_NAME[c] for c in conds], widths=0.5)
    ax.set_ylabel("Seconds per case")
    ax.set_title("Time per case")
    fig.tight_layout()
    figs["time_by_condition"] = fig

    if not quest.empty:
        fig, ax = plt.subplots(figsize=(4.6, 3.4))
        labels = ["SUS", "NASA-TLX"]
        for i, c in enumerate(conds):
            q = quest[quest.condition == c]
            ax.bar(np.arange(2) + (i - 0.5) * 0.36, [q["sus"].mean(), q["tlx"].mean()], 0.36,
                   label=COND_NAME[c], color=COLORS[c])
        ax.set_xticks(np.arange(2), labels)
        ax.set_ylim(0, 100)
        ax.set_title("Usability (higher better) and workload (lower better)", fontsize=9)
        ax.legend(frameon=False)
        fig.tight_layout()
        figs["questionnaires_by_condition"] = fig

    cat = by_category(resp)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    x = np.arange(len(cat))
    for i, c in enumerate(conds):
        col = f"Acceptance rate: {COND_NAME[c]}"
        if col in cat:
            ax.bar(x + (i - 0.5) * 0.36, cat[col], 0.36, label=COND_NAME[c], color=COLORS[c])
    ax.set_xticks(x, [c.replace("_", "\n") for c in cat.index], fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Acceptance rate")
    ax.set_title("Acceptance by case category (seeded errors should be low)")
    ax.legend(frameon=False)
    fig.tight_layout()
    figs["acceptance_by_category"] = fig
    return figs


def run_analysis(save: bool = True) -> dict:
    adj = load_adjudication()
    calib, calib_lines, calib_fig = layer_calibration(adj)
    res = {"layer_calibration": calib, "layer_summary": calib_lines, "figures": {}, "n_responses": 0,
           "n_participants": 0, "main_table": None, "by_category": None, "stats": None,
           "judge_agreement": [], "notes": []}
    if calib_fig is not None:
        res["figures"]["reliability_vs_correctness"] = calib_fig

    resp, quest = _read(RESPONSES_CSV), _read(QUESTIONNAIRES_CSV)
    # If a participant repeated a case or questionnaire (e.g. restarted session), keep the last answer.
    if not resp.empty:
        resp = resp.drop_duplicates(["participant_id", "condition", "case_id"], keep="last")
    if not quest.empty:
        quest = quest.drop_duplicates(["participant_id", "condition"], keep="last")
    if not resp.empty:
        resp = resp.drop(columns=[c for c in ["output_correct"] if c in resp])
        resp = resp.merge(adj[["case_id", "output_correct"]], on="case_id", how="left")
        resp["output_correct"] = resp["output_correct"].fillna(True).astype(bool)
        if not quest.empty:
            quest["sus"] = quest[[f"sus_{i}" for i in range(1, 11)]].apply(lambda r: sus_score(list(r)), axis=1)
            quest["tlx"] = quest[TLX_COLS].apply(lambda r: tlx_raw(list(r)), axis=1)
            quest["trust"] = quest[["trust_1", "trust_2", "trust_3"]].mean(axis=1)
        table, notes = main_comparison(resp, quest)
        res.update(n_responses=len(resp), n_participants=resp["participant_id"].nunique(), main_table=table,
                   notes=notes, by_category=by_category(resp), stats=paired_tests(resp, quest),
                   judge_agreement=judge_vs_clinicians(resp, adj))
        res["figures"].update(_figures(resp, quest, table))

    if outputs_meta().get("provider") == "mock":
        res["notes"].insert(0, "WARNING: AI outputs come from the mock simulator. These numbers are not findings.")

    if save:
        out = config.REPORT_DIR
        if calib is not None:
            calib.to_csv(out / "layer_calibration.csv")
        if res["main_table"] is not None:
            res["main_table"].to_csv(out / "results_table.csv")
            (out / "results_table.md").write_text(_md(res), encoding="utf-8")
            res["by_category"].to_csv(out / "acceptance_by_category.csv")
            if res["stats"] is not None:
                res["stats"].to_csv(out / "paired_tests.csv", index=False)
        for name, fig in res["figures"].items():
            fig.savefig(config.FIGURES_DIR / f"{name}.png", dpi=200, bbox_inches="tight")
    return res


def _md(res: dict) -> str:
    parts = ["# Results: LLM only vs LLM + layer", ""]
    parts += [f"_{n}_" for n in res["notes"]] + [""]
    try:
        parts += [res["main_table"].to_markdown(), ""]
    except ImportError:  # 'tabulate' not installed
        parts += ["```", res["main_table"].to_string(), "```", ""]
    if res["layer_calibration"] is not None:
        parts += ["## Reliability indicator vs correctness", "", res["layer_calibration"].to_string(), ""]
        parts += [f"- {x}" for x in res["layer_summary"]]
    if res["judge_agreement"]:
        parts += ["", "## Automated judge vs clinicians", ""] + [f"- {x}" for x in res["judge_agreement"]]
    return "\n".join(parts)


if __name__ == "__main__":
    r = run_analysis(save=True)
    pd.set_option("display.width", 160)
    print("\n== Reliability indicator vs correctness ==")
    print(r["layer_calibration"])
    for line in r["layer_summary"]:
        print(" ", line)
    if r["main_table"] is None:
        print("\nNo participant responses yet (data/results/responses.csv).")
    else:
        print(f"\n== LLM only vs LLM + layer: {r['n_participants']} participants ==")
        print(r["main_table"])
        for n in r["notes"]:
            print(" ", n)
        print("\n== By category ==")
        print(r["by_category"])
        if r["stats"] is not None:
            print("\n== Paired tests ==")
            print(r["stats"])
        for line in r["judge_agreement"]:
            print(" ", line)
    print(f"\nTables in {config.REPORT_DIR}, figures in {config.FIGURES_DIR}")
