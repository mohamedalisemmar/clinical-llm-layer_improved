"""Run the LLM + intermediary layer on every case ONCE and cache the results.

Why precompute? Every participant must see exactly the same AI output for a
given case, and sessions must not wait for 10+ API calls per case.

Usage (from the project root):
    python -m scripts.precompute_outputs                 # all cases, provider from .env
    python -m scripts.precompute_outputs --only S01 E01  # some cases
    python -m scripts.precompute_outputs --provider mock # offline test run
    python -m scripts.precompute_outputs --force         # recompute existing outputs
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from evaluation.grading import auto_grade  # noqa: E402
from layer.pipeline import run_layer  # noqa: E402
from llm.client import get_client  # noqa: E402
from storage import load_cases  # noqa: E402

ADJ_FIELDS = ["case_id", "category", "case_set", "shown_diagnosis", "reference_diagnosis",
              "injected", "layer_reliability", "auto_correct", "output_correct", "adjudicated_by", "notes"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    client = get_client(args.provider, args.model)
    cases = load_cases()
    if args.only:
        cases = [c for c in cases if c["id"] in set(args.only)]
    print(f"Provider: {client.provider}  Model: {client.model}  Cases: {len(cases)}\n")

    for case in cases:
        path = config.OUTPUTS_DIR / f"{case['id']}.json"
        if path.exists() and not args.force:
            print(f"  {case['id']}: exists, skipped (use --force to recompute)")
            continue
        out = run_layer(case, client, progress=lambda m: None)
        data = out.model_dump()
        data["auto_correct"] = auto_grade(case, out.structured.primary_diagnosis, out.injected, client)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {case['id']}  {case['category']:<20} {out.reliability.level:<9} "
              f"correct={data['auto_correct']!s:<5} calls={out.n_llm_calls:<3} {out.structured.primary_diagnosis[:45]}")

    (config.OUTPUTS_DIR / "_meta.json").write_text(json.dumps({
        "provider": client.provider, "model": client.model,
        "n_samples": config.N_SAMPLES, "sample_temperature": config.SAMPLE_TEMPERATURE,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")
    write_adjudication()
    print(f"\nOutputs in {config.OUTPUTS_DIR}")
    print(f"Review and correct {config.ADJUDICATION_PATH} (column output_correct) before the study.")
    if client.provider == "mock":
        print("\nWARNING: mock outputs are for testing only. Re-run with a real LLM before the study.")


def write_adjudication() -> None:
    existing = {}
    if config.ADJUDICATION_PATH.exists():
        with open(config.ADJUDICATION_PATH, encoding="utf-8") as f:
            existing = {r["case_id"]: r for r in csv.DictReader(f)}
    rows = []
    for case in load_cases():
        p = config.OUTPUTS_DIR / f"{case['id']}.json"
        if not p.exists():
            continue
        o = json.loads(p.read_text(encoding="utf-8"))
        prev = existing.get(case["id"], {})
        auto = str(bool(o.get("auto_correct"))).lower()
        same_answer = prev.get("shown_diagnosis") == o["structured"]["primary_diagnosis"]
        manual = prev.get("adjudicated_by") and same_answer
        rows.append({
            "case_id": case["id"], "category": case["category"], "case_set": case["set"],
            "shown_diagnosis": o["structured"]["primary_diagnosis"],
            "reference_diagnosis": case["reference_diagnosis"],
            "injected": str(o.get("injected", False)).lower(),
            "layer_reliability": o["reliability"]["level"],
            "auto_correct": auto,
            "output_correct": prev["output_correct"] if manual else auto,
            "adjudicated_by": prev.get("adjudicated_by", "") if manual else "",
            "notes": prev.get("notes", "") if manual else "",
        })
    with open(config.ADJUDICATION_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ADJ_FIELDS)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
