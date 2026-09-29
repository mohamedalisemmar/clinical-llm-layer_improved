"""The aggregation rule from Chapter 1, Section 3.4.2, as executable tests."""
from layer.reliability import aggregate
from layer.schemas import Signal


def sigs(cons="pass", agree="pass", contra="pass", compl="pass", missing="pass", incons="pass", verbal="pass"):
    return [
        Signal(name="consistency", label="", status=cons, detail="5 of 5 repeated answers gave the same diagnosis."
               if cons == "pass" else "2 of 5 repeated answers gave the same diagnosis."),
        Signal(name="prompt_agreement", label="", status=agree),
        Signal(name="contradiction", label="", status=contra, detail="X conflicts with Y."),
        Signal(name="completeness", label="", status=compl),
        Signal(name="missing_information", label="", status=missing, detail="Critical data missing: ECG; troponin."),
        Signal(name="input_inconsistency", label="", status=incons),
        Signal(name="verbal_confidence", label="", status=verbal, value="low" if verbal == "warn" else "high"),
    ]


def test_all_pass_is_high():
    assert aggregate(sigs()).level == "HIGH"


def test_contradiction_alone_is_low():
    r = aggregate(sigs(contra="fail"))
    assert r.level == "LOW" and r.verify_independently


def test_consistency_failure_alone_is_low():
    assert aggregate(sigs(cons="fail")).level == "LOW"


def test_stable_but_incomplete_is_moderate():
    """The clinically important case: consistent answer, key data missing -> must not read as High."""
    r = aggregate(sigs(missing="warn"))
    assert r.level == "MODERATE"
    assert "missing" in r.explanation


def test_prompt_disagreement_prevents_high_but_is_not_low():
    assert aggregate(sigs(agree="fail")).level == "MODERATE"


def test_verbal_confidence_can_only_lower():
    assert aggregate(sigs(verbal="warn")).level == "MODERATE"
    assert aggregate(sigs(cons="fail", verbal="pass")).level == "LOW"


def test_explanation_always_present():
    for s in (sigs(), sigs(missing="warn"), sigs(contra="fail")):
        assert aggregate(s).explanation
