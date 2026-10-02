"""Thin Gemini API client: structured JSON output, rate limiting, retries, and a disk cache.

Only synthetic data is ever sent (free-tier inputs may be used by Google to improve its products).
The API key comes from the GEMINI_API_KEY environment variable (Kaggle Secret / HF Space secret), never from code.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")


class GeminiUnavailable(RuntimeError):
    pass


def load_key_on_kaggle(secret_name: str = "GEMINI_API_KEY") -> str:
    """Find the Gemini key on Kaggle without ever printing it.

    Order: Kaggle Secret (Add-ons -> Secrets) -> environment variable -> a file named gemini_key.txt inside an attached
    PRIVATE Kaggle dataset (fallback if secrets are not available in a background run). Returns where it was found.
    """
    if os.environ.get(secret_name):
        return "environment"
    try:
        from kaggle_secrets import UserSecretsClient

        value = UserSecretsClient().get_secret(secret_name)
        if value:
            os.environ[secret_name] = value.strip()
            return "kaggle_secret"
    except Exception:  # noqa: BLE001 - not on Kaggle, secret not attached, or not available in this run
        pass
    for p in Path("/kaggle/input").glob("**/gemini_key.txt") if Path("/kaggle/input").exists() else []:
        value = p.read_text(encoding="utf-8").strip()
        if value:
            os.environ[secret_name] = value
            return "private_dataset_file"
    return "not_found"


class Gemini:
    def __init__(self, model: str | None = None, min_interval_s: float = 6.5, cache_dir: str | Path | None = None,
                 max_retries: int = 4, timeout_s: float = 60.0):
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise GeminiUnavailable("GEMINI_API_KEY is not set")
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:  # pragma: no cover
            raise GeminiUnavailable("pip install google-genai") from e
        self._types = types
        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))
        self.models = [model or DEFAULT_MODEL, FALLBACK_MODEL]
        self.min_interval_s, self.max_retries = min_interval_s, max_retries
        self._last = 0.0
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.calls = self.cache_hits = self.failures = 0

    def _key(self, prompt: str, schema_name: str, temperature: float) -> str:
        return hashlib.sha256(f"{self.models[0]}|{schema_name}|{temperature}|{prompt}".encode()).hexdigest()[:24]

    def json(self, prompt: str, schema, temperature: float = 0.7, system: str | None = None):
        """Return parsed JSON that follows `schema` (a Python type / pydantic model), or raise GeminiUnavailable."""
        name = getattr(schema, "__name__", str(schema))
        key = self._key((system or "") + prompt, name, temperature)
        if self.cache_dir and (self.cache_dir / f"{key}.json").exists():
            self.cache_hits += 1
            return json.loads((self.cache_dir / f"{key}.json").read_text(encoding="utf-8"))
        last_err = None
        for model in self.models:
            for attempt in range(self.max_retries):
                wait = self.min_interval_s - (time.time() - self._last)
                if wait > 0:
                    time.sleep(wait)
                self._last = time.time()
                try:
                    self.calls += 1
                    cfg = self._types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema,
                                                            temperature=temperature, system_instruction=system)
                    resp = self.client.models.generate_content(model=model, contents=prompt, config=cfg)
                    if not resp.text:
                        raise ValueError("empty response (possibly blocked)")
                    data = json.loads(resp.text)
                    if self.cache_dir:
                        (self.cache_dir / f"{key}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                    return data
                except Exception as e:  # noqa: BLE001 - network/API errors are retried, then we fall back
                    last_err = e
                    msg = str(e)
                    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "503" in msg or "timeout" in msg.lower():
                        time.sleep(min(60, 5 * 2 ** attempt))
                        continue
                    break  # non-retryable for this model -> try the fallback model
        self.failures += 1
        raise GeminiUnavailable(f"Gemini failed: {last_err!r}"[:300])

    def ping(self) -> dict:
        """One tiny request to check the key, region and quota before a long run."""
        out = self.json("Reply with a JSON list containing the single word ok.", list[str], temperature=0.0)
        return {"ok": bool(out), "model": self.models[0]}

    def stats(self) -> dict:
        return {"model": self.models[0], "fallback_model": self.models[1], "calls": self.calls,
                "cache_hits": self.cache_hits, "failures": self.failures}
