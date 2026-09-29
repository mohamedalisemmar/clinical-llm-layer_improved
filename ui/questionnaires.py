"""Standard post-block questionnaires: SUS, NASA-TLX (raw), trust items."""

SUS_ITEMS = [
    "I think that I would like to use this system frequently.",
    "I found the system unnecessarily complex.",
    "I thought the system was easy to use.",
    "I think that I would need the support of a technical person to be able to use this system.",
    "I found the various functions in this system were well integrated.",
    "I thought there was too much inconsistency in this system.",
    "I would imagine that most people would learn to use this system very quickly.",
    "I found the system very cumbersome to use.",
    "I felt very confident using the system.",
    "I needed to learn a lot of things before I could get going with this system.",
]
LIKERT_5 = ["1 Strongly disagree", "2", "3", "4", "5 Strongly agree"]

TLX_ITEMS = [
    ("tlx_mental", "Mental demand", "How mentally demanding was the task?", "Very low", "Very high"),
    ("tlx_physical", "Physical demand", "How physically demanding was the task?", "Very low", "Very high"),
    ("tlx_temporal", "Temporal demand", "How hurried or rushed was the pace of the task?", "Very low", "Very high"),
    ("tlx_performance", "Performance", "How successful were you in accomplishing what you were asked to do?",
     "Perfect", "Failure"),
    ("tlx_effort", "Effort", "How hard did you have to work to accomplish your level of performance?",
     "Very low", "Very high"),
    ("tlx_frustration", "Frustration", "How insecure, discouraged, irritated, stressed and annoyed were you?",
     "Very low", "Very high"),
]

TRUST_ITEMS = [
    "I could tell when the AI's recommendation should not be relied on.",
    "The information displayed helped me decide how much to rely on the AI.",
    "I felt in control of the final decision.",
]
