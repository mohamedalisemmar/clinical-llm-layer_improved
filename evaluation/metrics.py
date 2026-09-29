"""Metric definitions (kept separate so they can be cited in the report)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sus_score(items: list[float]) -> float:
    """System Usability Scale (Brooke, 1996): 10 items on 1-5 -> 0-100.
    Odd items contribute (x - 1), even items (5 - x); the sum is multiplied by 2.5."""
    if len(items) != 10 or any(pd.isna(items)):
        return float("nan")
    total = sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(items))
    return total * 2.5


def tlx_raw(values: list[float]) -> float:
    """Raw NASA-TLX: unweighted mean of the six 0-100 subscales (lower = less workload)."""
    return float(np.mean(values)) if values else float("nan")


def reliance_metrics(df: pd.DataFrame) -> dict:
    """Trust-calibration metrics from accept/reject decisions.

    error_detection      = P(reject | AI output incorrect)   higher is better
    correct_acceptance   = P(accept | AI output correct)     higher is better
    commission_errors    = P(accept | AI output incorrect)   lower is better  (automation bias)
    appropriate_reliance = share of decisions that accept correct and reject incorrect outputs
    """
    acc = df["decision"].eq("accept")
    corr = df["output_correct"].astype(bool)
    n_inc, n_cor = int((~corr).sum()), int(corr.sum())
    return {
        "n": len(df),
        "error_detection": (~acc & ~corr).sum() / n_inc if n_inc else np.nan,
        "correct_acceptance": (acc & corr).sum() / n_cor if n_cor else np.nan,
        "commission_errors": (acc & ~corr).sum() / n_inc if n_inc else np.nan,
        "appropriate_reliance": ((acc & corr) | (~acc & ~corr)).mean() if len(df) else np.nan,
    }


PERCEIVED = {"Low": 1, "Moderate": 2, "High": 3}
AGREEMENT = {"Disagree": 1, "Partially agree": 2, "Agree": 3}


def perceived_discrimination(df: pd.DataFrame) -> float:
    """Mean perceived reliability (Low=1..High=3) on correct outputs minus on incorrect ones.
    Positive = participants rated correct answers as more reliable (good calibration)."""
    p = df["perceived_reliability"].map(PERCEIVED)
    corr = df["output_correct"].astype(bool)
    if corr.all() or (~corr).all():
        return float("nan")
    return float(p[corr].mean() - p[~corr].mean())
