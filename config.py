"""Central configuration. Values come from environment variables (.env file)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:  # python-dotenv is optional
    pass


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# ---- LLM backend -----------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "mock": "mock-clinical-simulator",
}

# ---- Reliability layer -----------------------------------------------------
N_SAMPLES = int(os.getenv("N_SAMPLES", "5"))
SAMPLE_TEMPERATURE = float(os.getenv("SAMPLE_TEMPERATURE", "1.0"))
BASELINE_TEMPERATURE = float(os.getenv("BASELINE_TEMPERATURE", "0.7"))
USE_LLM_CONTRADICTION_CHECK = _bool("USE_LLM_CONTRADICTION_CHECK", True)
USE_LLM_JUDGE = _bool("USE_LLM_JUDGE", True)
USE_LLM_EQUIVALENCE = _bool("USE_LLM_EQUIVALENCE", True)

# Consistency thresholds (fraction of repeated generations agreeing with the
# answer shown to the clinician). With N=5: 5/5 or 4/5 -> pass, 3/5 -> warn,
# 2/5 or fewer -> fail.
CONSISTENCY_PASS = 0.8
CONSISTENCY_WARN = 0.6

# ---- Study session ---------------------------------------------------------
MAX_CASES_PER_BLOCK = int(os.getenv("MAX_CASES_PER_BLOCK", "0"))

# ---- Paths -----------------------------------------------------------------
DATA_DIR = ROOT / "data"
CASES_PATH = DATA_DIR / "cases.json"
OUTPUTS_DIR = DATA_DIR / "outputs"          # precomputed LLM + layer outputs
RESULTS_DIR = DATA_DIR / "results"          # participant responses (CSV)
ADJUDICATION_PATH = OUTPUTS_DIR / "adjudication.csv"
REPORT_DIR = ROOT / "results"               # analysis tables
FIGURES_DIR = REPORT_DIR / "figures"

for _d in (OUTPUTS_DIR, RESULTS_DIR, REPORT_DIR, FIGURES_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def model_name() -> str:
    return LLM_MODEL or DEFAULT_MODELS.get(LLM_PROVIDER, "")
