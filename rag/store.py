"""ChromaDB vector store. One collection per (embedder, chunking-config) so that different
strategies can be compared side by side without re-embedding everything each time."""
from __future__ import annotations

import hashlib

import chromadb

from . import config
from .chunking import Chunk
from .embeddings import Embedder


def collection_name(embedder: str, strategy: str, size: int, overlap: int, model: str = "") -> str:
    raw = f"{embedder}|{model}|{strategy}|{size}|{overlap}"
    return f"rag_{embedder}_{strategy}_{hashlib.md5(raw.encode()).hexdigest()[:8]}"


class VectorStore:
    def __init__(self, name: str, embedder: Embedder, path=None):
        self.client = chromadb.PersistentClient(path=str(path or config.CHROMA_DIR))
        self.col = self.client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
        self.embedder = embedder

    # ----------------------------------------------------------- indexing
    def has_doc(self, doc_id: str) -> bool:
        return bool(self.col.get(where={"doc_id": doc_id}, limit=1)["ids"])

    def add_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        for i in range(0, len(chunks), 128):
            batch = chunks[i:i + 128]
            self.col.upsert(
                ids=[f"{c.doc_id}:{c.chunk_index}" for c in batch],
                documents=[c.text for c in batch],
                embeddings=self.embedder.embed([c.text for c in batch]),
                metadatas=[{"doc_id": c.doc_id, "doc_name": c.doc_name,
                            "locator": c.locator, "chunk_index": c.chunk_index} for c in batch],
            )
        return len(chunks)

    def delete_doc(self, doc_id: str) -> None:
        self.col.delete(where={"doc_id": doc_id})

    def count(self) -> int:
        return self.col.count()

    # ----------------------------------------------------------- search
    def search(self, query: str, k: int = 5, doc_ids: list[str] | None = None) -> list[dict]:
        if self.count() == 0:
            return []
        where = None
        if doc_ids:
            where = {"doc_id": doc_ids[0]} if len(doc_ids) == 1 else {"doc_id": {"$in": doc_ids}}
        res = self.col.query(query_embeddings=self.embedder.embed([query]),
                             n_results=min(k, self.count()), where=where)
        hits = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append({"text": text, "score": round(1 - dist, 4), **meta})   # cosine similarity
        return hits
