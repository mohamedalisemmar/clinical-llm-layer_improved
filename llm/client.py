"""LLM client abstraction.

Every call goes through `LLMClient.complete(system, user, task=..., meta=...)`.
Real providers ignore `task` and `meta`; the mock provider uses them to
simulate plausible behaviour offline.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

import config


class LLMError(RuntimeError):
    pass


class LLMClient:
    provider = "base"

    def __init__(self, model: str):
        self.model = model
        self.n_calls = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        task: str,
        meta: Optional[dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        last_err: Exception | None = None
        for attempt in range(4):
            try:
                self.n_calls += 1
                return self._complete(system, user, task=task, meta=meta or {},
                                      temperature=temperature, max_tokens=max_tokens)
            except Exception as err:  # network / rate-limit errors
                last_err = err
                time.sleep(2 ** attempt)
        raise LLMError(f"{self.provider} call failed after retries: {last_err}")

    def _complete(self, system, user, *, task, meta, temperature, max_tokens) -> str:
        raise NotImplementedError


class AnthropicClient(LLMClient):
    provider = "anthropic"

    def __init__(self, model: str):
        super().__init__(model)
        import anthropic  # imported lazily so the package is optional
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY is not set (see .env.example)")
        self._client = anthropic.Anthropic()

    def _complete(self, system, user, *, task, meta, temperature, max_tokens) -> str:
        resp = self._client.messages.create(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


class OpenAICompatClient(LLMClient):
    """OpenAI, Groq, OpenRouter, Ollama, LM Studio... anything OpenAI-compatible."""
    provider = "openai"

    def __init__(self, model: str):
        super().__init__(model)
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY") or ("ollama" if config.OPENAI_BASE_URL else None)
        if not api_key:
            raise LLMError("OPENAI_API_KEY is not set (see .env.example)")
        self._client = OpenAI(api_key=api_key, base_url=config.OPENAI_BASE_URL)

    def _complete(self, system, user, *, task, meta, temperature, max_tokens) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


def get_client(provider: Optional[str] = None, model: Optional[str] = None) -> LLMClient:
    provider = (provider or config.LLM_PROVIDER).lower()
    model = model or config.LLM_MODEL or config.DEFAULT_MODELS.get(provider, "")
    if provider == "mock":
        from llm.mock import MockClient
        return MockClient(model or "mock-clinical-simulator")
    if provider == "anthropic":
        return AnthropicClient(model)
    if provider == "openai":
        return OpenAICompatClient(model)
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (use mock, anthropic or openai)")
