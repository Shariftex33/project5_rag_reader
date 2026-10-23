"""Embedding back-ends behind one tiny interface: `embed(list[str]) -> list[list[float]]`.

  hash    - offline TF-IDF-style hashing vectors. Zero downloads, zero API keys.
            Lexical only, but great for tests, CI and a fallback demo.
  minilm  - Chroma's bundled ONNX all-MiniLM-L6-v2 (local, ~80 MB downloaded once).
  ollama  - any Ollama embedding model (default nomic-embed-text)  [local]
  openai  - text-embedding-3-small (cloud)
"""
from __future__ import annotations

import hashlib
import math
import re

from . import config

EMBEDDERS = ("minilm", "ollama", "openai", "hash")

_STOP = set("a an the of to in is are was were be been and or for on with as by at from that this it its into than then which who whom".split())


class Embedder:
    name = "base"
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class HashEmbedder(Embedder):
    """Hashing-trick bag-of-words (unigrams + bigrams), L2-normalised."""
    name = "hash"
    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        toks = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]
        toks = [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in toks]   # crude stemming
        feats = toks + [a + "_" + b for a, b in zip(toks, toks[1:])]
        v = [0.0] * self.dim
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest(), 16)
            v[h % self.dim] += (1.0 if (h >> 64) & 1 else -1.0) * (1.4 if "_" in f else 1.0)
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed(self, texts):
        return [self._vec(t) for t in texts]


class MiniLMEmbedder(Embedder):
    name = "minilm"
    def __init__(self):
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        self.fn = ONNXMiniLM_L6_V2()

    def embed(self, texts):
        return [list(map(float, v)) for v in self.fn(texts)]


class OllamaEmbedder(Embedder):
    name = "ollama"
    def __init__(self, model: str | None = None):
        self.model = model or config.OLLAMA_EMBED_MODEL

    def embed(self, texts):
        import requests
        out = []
        for i in range(0, len(texts), 32):
            r = requests.post(f"{config.OLLAMA_URL}/api/embed",
                              json={"model": self.model, "input": texts[i:i + 32]}, timeout=300)
            if r.status_code == 404:
                raise RuntimeError(f"Ollama model '{self.model}' not found. Run: ollama pull {self.model}")
            r.raise_for_status()
            out.extend(r.json()["embeddings"])
        return out


class OpenAIEmbedder(Embedder):
    name = "openai"
    def __init__(self, api_key: str | None = None, model: str | None = None):
        from openai import OpenAI
        key = api_key or config.OPENAI_API_KEY
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set (put it in .env or the sidebar).")
        self.client, self.model = OpenAI(api_key=key), model or config.OPENAI_EMBED_MODEL

    def embed(self, texts):
        out = []
        for i in range(0, len(texts), 96):
            resp = self.client.embeddings.create(model=self.model, input=texts[i:i + 96])
            out.extend(d.embedding for d in resp.data)
        return out


def get_embedder(name: str, **kw) -> Embedder:
    if name == "hash":
        return HashEmbedder()
    if name == "minilm":
        return MiniLMEmbedder()
    if name == "ollama":
        return OllamaEmbedder(kw.get("model"))
    if name == "openai":
        return OpenAIEmbedder(kw.get("api_key"), kw.get("model"))
    raise ValueError(f"Unknown embedder {name!r}; choose from {EMBEDDERS}")
