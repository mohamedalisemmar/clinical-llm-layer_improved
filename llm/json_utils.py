"""Robust extraction of JSON objects from LLM text output."""
import json
import re
from typing import Any


class JSONParseError(ValueError):
    pass


def parse_json(text: str) -> Any:
    """Return the first JSON object/array found in `text`.

    Handles ```json fences, leading prose and trailing commentary.
    """
    if text is None:
        raise JSONParseError("empty response")
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Find the first balanced {...} or [...] block.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        while start != -1:
            depth, in_str, esc = 0, False, False
            for i in range(start, len(cleaned)):
                ch = cleaned[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
            start = cleaned.find(opener, start + 1)
    raise JSONParseError(f"no valid JSON found in response: {text[:200]!r}")


def call_json(client, system: str, user: str, *, task: str, meta=None,
              temperature: float = 0.0, retries: int = 1):
    """Call the LLM and parse JSON, retrying once with a reminder if parsing fails."""
    prompt = user
    last = None
    for _ in range(retries + 1):
        text = client.complete(system, prompt, task=task, meta=meta, temperature=temperature)
        try:
            return parse_json(text)
        except JSONParseError as err:
            last = err
            prompt = user + "\n\nIMPORTANT: your previous answer was not valid JSON. Return ONLY the JSON object."
    raise last
