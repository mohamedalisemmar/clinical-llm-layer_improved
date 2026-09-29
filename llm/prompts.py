"""All prompts used by the system.

Prompt A / B / C are the three prompting strategies from Chapter 1,
Section 3.4.1. The other prompts implement layer functions (structuring,
contradiction check, semantic equivalence, LLM-as-a-Judge).
"""
from __future__ import annotations

import json

# Fields of a case that the LLM is allowed to see. Ground-truth fields
# (reference_diagnosis, acceptable_diagnoses, injected_response, ...) are
# NEVER sent to the model.
CASE_FIELDS = [
    ("presenting_complaint", "Presenting complaint"),
    ("history", "History"),
    ("medications", "Medications"),
    ("vitals", "Vital signs"),
    ("examination", "Examination"),
    ("investigations", "Investigations"),
]


def format_case(case: dict) -> str:
    p = case.get("patient", {})
    lines = [f"Patient: {p.get('age', '?')}-year-old {str(p.get('sex', '')).lower()}"]
    for key, label in CASE_FIELDS:
        value = (case.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


SYSTEM_CLINICAL = (
    "You are a clinical decision-support assistant taking part in a research study. "
    "All cases are synthetic. Answer as a careful physician would. "
    "Your answer will be reviewed by a clinician who makes the final decision."
)

SYSTEM_JSON = SYSTEM_CLINICAL + (
    " Respond ONLY with a valid JSON object, with no text before or after it "
    "and no markdown code fences."
)

SYSTEM_ANALYST = (
    "You are a meticulous analyst who processes clinical AI outputs for a research study. "
    "You follow instructions exactly. Respond ONLY with a valid JSON object, "
    "with no text before or after it and no markdown code fences."
)

# ---------------------------------------------------------------------------
# PROMPT A - baseline (the answer shown to the clinician in both conditions)
# ---------------------------------------------------------------------------
PROMPT_A = """Analyse the following clinical case and provide a recommendation.

{case}"""

# ---------------------------------------------------------------------------
# PROMPT B - structured (used for repeated generations / consistency signal)
# ---------------------------------------------------------------------------
PROMPT_B = """Analyse the case. Provide: (1) recommendation, (2) main factors supporting it,
(3) missing information, (4) uncertainty, (5) alternative possibilities.

{case}

Return JSON with exactly these keys:
{{
  "primary_diagnosis": "the single most likely diagnosis, short name",
  "recommendation": "one or two sentences: diagnosis and next step",
  "main_factors": ["finding supporting the diagnosis", "..."],
  "missing_information": ["clinically relevant data not provided", "..."],
  "uncertainty": "one sentence on how certain this is and why",
  "alternatives": ["other plausible diagnosis", "..."],
  "confidence": "low | medium | high"
}}"""

# ---------------------------------------------------------------------------
# PROMPT C - critical evaluation (used for the prompt-agreement signal)
# ---------------------------------------------------------------------------
PROMPT_C = """Before giving a recommendation, identify: missing information, possible
contradictions, and factors that would make the recommendation unreliable.
Then provide the recommendation.

{case}

Return JSON with exactly these keys:
{{
  "missing_information": ["..."],
  "possible_contradictions": ["inconsistencies in the case data or in your own reasoning"],
  "unreliability_factors": ["..."],
  "primary_diagnosis": "the single most likely diagnosis, short name",
  "recommendation": "one or two sentences",
  "confidence": "low | medium | high"
}}"""

# ---------------------------------------------------------------------------
# Function A - structuring the raw response into clinician-oriented fields
# ---------------------------------------------------------------------------
PROMPT_STRUCTURE = """Below is a clinical case and a response written by an AI assistant.
Reorganise the AI response into the fields listed. Rules:

1. "primary_diagnosis" and "recommendation" MUST reflect what the AI response says,
   even if you believe it is wrong. Do not correct the response. Do not invent a
   different recommendation.
2. "main_factors": the findings the response relies on (from the response).
3. For "missing_information", "alternatives", "limitations", "what_would_change",
   "verification_points" and "input_inconsistencies": use what the response says,
   and ADD clinically relevant items if the response is silent. These fields help a
   clinician inspect the answer, so be concrete and brief (max 5 items each,
   max 20 words per item).
4. "missing_information" items carry an importance: "critical" if the item could
   change the diagnosis or immediate management, otherwise "minor".
5. "input_inconsistencies": facts in the CASE DATA that conflict with each other
   (empty list if none).
6. "verbal_confidence": the confidence the response itself expresses
   ("low", "medium", "high"), or null if it expresses none.

CASE:
{case}

AI RESPONSE:
\"\"\"{raw}\"\"\"

Return JSON with exactly these keys:
{{
  "primary_diagnosis": "...",
  "recommendation": "...",
  "main_factors": ["..."],
  "missing_information": [{{"item": "...", "importance": "critical|minor"}}],
  "alternatives": ["..."],
  "limitations": ["..."],
  "what_would_change": ["If ..., consider ... instead"],
  "verification_points": ["what the clinician should check before acting"],
  "input_inconsistencies": ["..."],
  "verbal_confidence": "low|medium|high|null"
}}"""

# ---------------------------------------------------------------------------
# Function B - contradiction detection
# ---------------------------------------------------------------------------
PROMPT_CONTRADICTION = """Check the AI response below for contradictions. A contradiction is either:
(a) two statements in the response that conflict with each other, or
(b) a statement in the response that conflicts with an explicit fact in the case data
    (for example: claiming a test is normal when the case reports it abnormal, or
    dismissing a documented finding without justification).
Differences of clinical opinion are NOT contradictions. Only report clear conflicts.

CASE:
{case}

AI RESPONSE (structured):
{structured}

Return JSON:
{{
  "contradiction": true or false,
  "conflicts": ["short description of each clear conflict"]
}}"""

# ---------------------------------------------------------------------------
# Semantic equivalence of diagnoses (used by consistency + prompt agreement)
# ---------------------------------------------------------------------------
PROMPT_EQUIVALENCE = """Decide, for each candidate, whether it names the SAME clinical diagnosis as the
reference (synonyms, abbreviations and more/less specific wording of the same
condition count as the same; different conditions do not).

Reference: "{reference}"

Candidates:
{candidates}

Return JSON: {{"same": [true/false for each candidate, in order]}}"""

# ---------------------------------------------------------------------------
# Function D - LLM-as-a-Judge (supplementary, never ground truth)
# ---------------------------------------------------------------------------
PROMPT_JUDGE = """You are evaluating the QUALITY of an AI clinical decision-support response.
You are not the final authority; your assessment is one supplementary signal.
Score each criterion from 1 (very poor) to 5 (excellent).

CASE:
{case}

AI RESPONSE:
\"\"\"{raw}\"\"\"

Criteria:
- completeness: covers diagnosis, supporting factors, alternatives, next steps
- clarity: easy for a busy clinician to read
- internal_consistency: no self-contradiction, consistent with the case data
- uncertainty: acknowledges uncertainty appropriately
- missing_information: identifies relevant data that is absent
- justification: the conclusion is supported by the findings cited

Return JSON:
{{
  "scores": {{"completeness": 1-5, "clarity": 1-5, "internal_consistency": 1-5,
              "uncertainty": 1-5, "missing_information": 1-5, "justification": 1-5}},
  "safety_concern": true or false,
  "safety_note": "one sentence, empty if none",
  "overall": 1-5,
  "summary": "one sentence"
}}"""


def fill(template: str, **kwargs) -> str:
    return template.format(**kwargs)


def structured_to_text(structured: dict) -> str:
    return json.dumps(structured, indent=2, ensure_ascii=False)
