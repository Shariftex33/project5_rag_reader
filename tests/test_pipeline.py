"""Offline tests (no LLM / network):  python -m pytest -q   (or python tests/test_pipeline.py)"""
import os, sys, tempfile
from pathlib import Path
os.environ["RAG_DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.chunking import chunk_document
from rag.loaders import Document, load_any
from rag.pipeline import RAGPipeline, RAGSettings

SAMPLES = Path(__file__).resolve().parent.parent / "sample_docs"


class FakeLLM:
    """Echoes the first context line so we can test prompting/condensing without a model."""
    def chat(self, messages, temperature=0.0):
        return "Mars"
    def stream(self, messages, temperature=0.0):
        yield "ok"


def test_chunk_sizes_and_overlap():
    doc = Document("d", "d", "txt", [("1", "Alpha beta gamma. " * 200)])
    for strat in ("fixed", "recursive", "sentence"):
        chunks = chunk_document(doc, strat, 300, 60)
        assert chunks and all(len(c.text) <= 300 for c in chunks)
    ch = chunk_document(doc, "fixed", 300, 60)
    assert ch[0].text[-30:].strip() in ch[1].text          # overlap preserved context


def test_all_formats_load():
    for p in SAMPLES.iterdir():
        d = load_any(str(p))
        assert d.n_chars > 500, p.name


def test_multi_doc_retrieval_and_scoping():
    pipe = RAGPipeline(RAGSettings(embedder="hash", top_k=3))
    docs = [load_any(str(p)) for p in sorted(SAMPLES.iterdir())]
    for d in docs:
        pipe.add_document(d)
    hit = pipe.retrieve("What is the home office stipend?")[0]
    assert hit["doc_name"] == "remote_work_policy.docx" and "600" in hit["text"]
    hit = pipe.retrieve("tallest volcano Olympus Mons")[0]
    assert hit["doc_name"] == "solar_system_guide.pdf"
    only_rag = [d.doc_id for d in docs if d.name == "intro_to_rag.txt"]
    assert {h["doc_name"] for h in pipe.retrieve("stipend", only_rag)} == {"intro_to_rag.txt"}


def test_no_hits_returns_not_found():
    pipe = RAGPipeline(RAGSettings(embedder="hash"), data_path=tempfile.mkdtemp())
    assert "couldn't find" in pipe.ask("anything", FakeLLM()).text


def test_followup_is_condensed():
    pipe = RAGPipeline(RAGSettings(embedder="hash"))
    q = pipe.condense("what about its moons?", [{"role": "user", "content": "Tell me about Mars"}], FakeLLM())
    assert q == "Mars"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
