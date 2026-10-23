"""The RAG pipeline: ingest -> chunk -> embed -> store; question -> (rewrite) -> retrieve -> generate."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .chunking import chunk_document
from .embeddings import get_embedder
from .llm import LLM
from .loaders import Document, delete_document, list_documents, save_document
from .store import VectorStore, collection_name

SYSTEM_PROMPT = """You are a careful document assistant. Answer the question using ONLY the numbered \
context passages below. Cite the passages you used like [1] or [2][3] right after the claim.
If the context does not contain the answer, reply exactly: "I couldn't find that in the uploaded documents." \
Do not use outside knowledge. Be concise."""

REWRITE_PROMPT = """Given the chat history and a follow-up question, rewrite the follow-up as ONE standalone \
search query that includes any names or topics it refers to. Output only the rewritten query."""

NOT_FOUND = "I couldn't find that in the uploaded documents."


@dataclass
class RAGSettings:
    embedder: str = "hash"
    embedder_kwargs: dict = field(default_factory=dict)
    strategy: str = config.DEFAULT_STRATEGY
    chunk_size: int = config.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = config.DEFAULT_CHUNK_OVERLAP
    top_k: int = config.DEFAULT_TOP_K
    min_score: float = 0.0             # drop hits below this cosine similarity


@dataclass
class Answer:
    text: str
    sources: list[dict]
    standalone_query: str


class RAGPipeline:
    def __init__(self, settings: RAGSettings | None = None, data_path=None):
        self.s = settings or RAGSettings()
        self.embedder = get_embedder(self.s.embedder, **self.s.embedder_kwargs)
        model = self.s.embedder_kwargs.get("model", "") or ""
        self.store = VectorStore(collection_name(self.s.embedder, self.s.strategy, self.s.chunk_size,
                                                 self.s.chunk_overlap, model), self.embedder, data_path)

    # ------------------------------------------------------------ ingestion
    def add_document(self, doc: Document) -> int:
        save_document(doc)
        return self.index_document(doc)

    def index_document(self, doc: Document) -> int:
        if self.store.has_doc(doc.doc_id):
            return 0
        chunks = chunk_document(doc, self.s.strategy, self.s.chunk_size, self.s.chunk_overlap)
        return self.store.add_chunks(chunks)

    def sync_index(self) -> int:
        """Index any stored document missing from the current collection (after a settings change)."""
        return sum(self.index_document(d) for d in list_documents())

    def remove_document(self, doc_id: str) -> None:
        delete_document(doc_id)
        self.store.delete_doc(doc_id)

    # ------------------------------------------------------------ querying
    def retrieve(self, query: str, doc_ids: list[str] | None = None) -> list[dict]:
        hits = self.store.search(query, self.s.top_k, doc_ids)
        return [h for h in hits if h["score"] >= self.s.min_score]

    @staticmethod
    def build_context(hits: list[dict]) -> str:
        return "\n\n".join(f"[{i}] (source: {h['doc_name']}, {h['locator']})\n{h['text']}"
                           for i, h in enumerate(hits, 1))

    def condense(self, question: str, history: list[dict], llm: LLM) -> str:
        """Turn a follow-up ('what about its cost?') into a standalone retrieval query."""
        if not history:
            return question
        convo = "\n".join(f"{m['role'].capitalize()}: {m['content'][:500]}" for m in history[-6:])
        out = llm.chat([{"role": "system", "content": REWRITE_PROMPT},
                        {"role": "user", "content": f"Chat history:\n{convo}\n\nFollow-up: {question}\n\nStandalone query:"}],
                       temperature=0.0).strip().strip('"')
        return out if 3 <= len(out) <= 400 else question

    def _messages(self, question: str, hits: list[dict], history: list[dict]) -> list[dict]:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT + "\n\nContext:\n" + self.build_context(hits)}]
        msgs += history[-4:]                       # short memory keeps small models focused
        msgs.append({"role": "user", "content": question})
        return msgs

    def ask(self, question: str, llm: LLM, history: list[dict] | None = None,
            doc_ids: list[str] | None = None) -> Answer:
        history = history or []
        query = self.condense(question, history, llm)
        hits = self.retrieve(query, doc_ids)
        if not hits:
            return Answer(NOT_FOUND, [], query)
        return Answer(llm.chat(self._messages(question, hits, history)), hits, query)

    def ask_stream(self, question: str, llm: LLM, history: list[dict] | None = None,
                   doc_ids: list[str] | None = None):
        """Returns (standalone_query, hits, token_generator) so the UI can show sources while streaming."""
        history = history or []
        query = self.condense(question, history, llm)
        hits = self.retrieve(query, doc_ids)
        if not hits:
            return query, [], iter([NOT_FOUND])
        return query, hits, llm.stream(self._messages(question, hits, history))
