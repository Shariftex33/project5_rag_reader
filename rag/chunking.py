"""Chunking strategies. All sizes are in characters (simple and model-agnostic).

fixed      - sliding window, ignores structure (baseline)
recursive  - split on paragraph -> line -> sentence -> word, then merge pieces up to
             `size`, carrying `overlap` characters of trailing context into the next chunk
sentence   - pack whole sentences, overlap = last N sentences that fit in `overlap` chars
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .loaders import Document

STRATEGIES = ("fixed", "recursive", "sentence")


@dataclass
class Chunk:
    text: str
    doc_id: str
    doc_name: str
    locator: str
    chunk_index: int


# ------------------------------------------------------------------ strategies
def fixed_split(text: str, size: int, overlap: int) -> list[str]:
    step = max(1, size - overlap)
    return [text[i:i + size].strip() for i in range(0, len(text), step) if text[i:i + size].strip()]


_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def split_sentences(text: str) -> list[str]:
    out = []
    for para in re.split(r"\n+", text):
        out.extend(s.strip() for s in _SENT.split(para) if s.strip())
    return out


def sentence_split(text: str, size: int, overlap: int) -> list[str]:
    sents, chunks, cur = split_sentences(text), [], []
    for s in sents:
        if cur and sum(len(x) + 1 for x in cur) + len(s) > size:
            chunks.append(" ".join(cur))
            carry, total = [], 0
            for x in reversed(cur):          # carry trailing sentences as overlap
                if total + len(x) > overlap:
                    break
                carry.insert(0, x)
                total += len(x) + 1
            cur = carry
        cur.append(s)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split_recursive(text: str, size: int, seps: list[str]) -> list[str]:
    """Break text into pieces no longer than `size`, preferring natural boundaries."""
    if len(text) <= size:
        return [text]
    if not seps:
        return fixed_split(text, size, 0)
    sep, rest = seps[0], seps[1:]
    parts = text.split(sep)
    pieces = []
    for i, p in enumerate(parts):
        p = p + (sep if i < len(parts) - 1 and sep.strip() else "")
        if len(p) > size:
            pieces.extend(_split_recursive(p, size, rest))
        elif p.strip():
            pieces.append(p)
    return pieces


def recursive_split(text: str, size: int, overlap: int) -> list[str]:
    pieces = _split_recursive(text, size, _SEPARATORS)
    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + len(p) > size:
            chunks.append(cur.strip())
            tail = cur[-overlap:] if overlap else ""
            # start the next chunk on a word boundary
            tail = tail[tail.find(" ") + 1:] if " " in tail and overlap else tail
            cur = tail
        cur += (" " if cur and not cur.endswith(("\n", " ")) else "") + p
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


_FUNCS = {"fixed": fixed_split, "recursive": recursive_split, "sentence": sentence_split}


# ------------------------------------------------------------------ public API
def chunk_document(doc: Document, strategy: str = "recursive", size: int = 800, overlap: int = 150) -> list[Chunk]:
    if strategy not in _FUNCS:
        raise ValueError(f"Unknown strategy {strategy!r}; choose from {STRATEGIES}")
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk size")
    fn, chunks, idx = _FUNCS[strategy], [], 0
    for locator, text in doc.sections:
        for piece in fn(text, size, overlap):
            chunks.append(Chunk(piece, doc.doc_id, doc.name, locator, idx))
            idx += 1
    return chunks
