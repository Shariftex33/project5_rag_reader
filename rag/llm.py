"""Chat back-ends: local Ollama (default qwen2.5:3b) or cloud OpenAI.
Both expose `chat(messages, stream=False)` taking OpenAI-style message dicts."""
from __future__ import annotations

import json
from typing import Iterator

from . import config


class LLM:
    provider = "base"
    def chat(self, messages: list[dict], temperature: float = 0.1) -> str:
        return "".join(self.stream(messages, temperature))
    def stream(self, messages: list[dict], temperature: float = 0.1) -> Iterator[str]:
        raise NotImplementedError


class OllamaLLM(LLM):
    provider = "ollama"
    def __init__(self, model: str | None = None, url: str | None = None, num_ctx: int = 4096):
        self.model, self.url, self.num_ctx = model or config.OLLAMA_CHAT_MODEL, (url or config.OLLAMA_URL).rstrip("/"), num_ctx

    def stream(self, messages, temperature=0.1):
        import requests
        try:
            r = requests.post(f"{self.url}/api/chat", stream=True, timeout=600, json={
                "model": self.model, "messages": messages, "stream": True,
                "options": {"temperature": temperature, "num_ctx": self.num_ctx}})
        except requests.ConnectionError:
            raise RuntimeError(f"Cannot reach Ollama at {self.url}. Start it with `ollama serve`.")
        if r.status_code == 404:
            raise RuntimeError(f"Model '{self.model}' not found. Run: ollama pull {self.model}")
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                if data.get("message", {}).get("content"):
                    yield data["message"]["content"]


class OpenAILLM(LLM):
    provider = "openai"
    def __init__(self, api_key: str | None = None, model: str | None = None):
        from openai import OpenAI
        key = api_key or config.OPENAI_API_KEY
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set (put it in .env or the sidebar).")
        self.client, self.model = OpenAI(api_key=key), model or config.OPENAI_CHAT_MODEL

    def stream(self, messages, temperature=0.1):
        resp = self.client.chat.completions.create(model=self.model, messages=messages,
                                                   temperature=temperature, stream=True)
        for ev in resp:
            if ev.choices and ev.choices[0].delta.content:
                yield ev.choices[0].delta.content


def get_llm(provider: str, **kw) -> LLM:
    if provider == "ollama":
        return OllamaLLM(kw.get("model"), kw.get("url"))
    if provider == "openai":
        return OpenAILLM(kw.get("api_key"), kw.get("model"))
    raise ValueError(f"Unknown LLM provider {provider!r}")


def ollama_models(url: str | None = None) -> list[str]:
    """List locally installed Ollama models (empty list if Ollama isn't running)."""
    import requests
    try:
        r = requests.get(f"{(url or config.OLLAMA_URL).rstrip('/')}/api/tags", timeout=3)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []
