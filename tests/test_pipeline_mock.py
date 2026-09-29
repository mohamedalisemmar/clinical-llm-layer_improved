"""End-to-end run of the layer with the offline mock provider."""
from layer.equivalence import rule_same
from layer.pipeline import run_layer
from llm.client import get_client
from llm.json_utils import parse_json
from llm.prompts import format_case
from storage import load_cases

CASES = {c["id"]: c for c in load_cases()}


def test_ground_truth_never_reaches_the_prompt():
    for case in CASES.values():
        text = format_case(case)
        assert case["reference_diagnosis"] not in text
        if case.get("injected_response"):
            assert case["injected_response"]["text"][:40] not in text


def test_seeded_errors_are_flagged_low():
    client = get_client("mock")
    for cid in ["E01", "E02", "E03", "E04", "E05", "E06"]:
        out = run_layer(CASES[cid], client)
        assert out.injected
        assert out.reliability.level == "LOW", cid


def test_straightforward_case_is_high_and_keeps_raw_answer():
    out = run_layer(CASES["S01"], get_client("mock"))
    assert out.reliability.level == "HIGH"
    assert out.raw_response.startswith("Most likely diagnosis")


def test_missing_information_case_is_not_high():
    out = run_layer(CASES["M03"], get_client("mock"))
    assert out.reliability.level != "HIGH"


def test_equivalence_rules():
    assert rule_same("Acute appendicitis", "Appendicitis")
    assert rule_same("STEMI", "ST elevation myocardial infarction")
    assert rule_same("Unstable angina", "Stable angina") is not True
    assert rule_same("Primary hypothyroidism", "Central (secondary) hypothyroidism") is not True


def test_parse_json_with_fences_and_prose():
    assert parse_json('Sure!\n```json\n{"a": [1, 2]}\n```\nDone') == {"a": [1, 2]}
