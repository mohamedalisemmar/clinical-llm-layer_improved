"""Quick check that the configured LLM provider works:  python -m scripts.test_llm_connection"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm.client import get_client  # noqa: E402

client = get_client()
print(f"Provider: {client.provider}  Model: {client.model}")
reply = client.complete("You are a helpful assistant.", "Reply with exactly: connection ok",
                        task="ping", meta={}, temperature=0)
print("Reply:", reply or "(empty - mock provider returns '{}' for unknown tasks)")
