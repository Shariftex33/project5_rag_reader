"""Streamlit UI for the Auto-Document Reader.   Run:  streamlit run app.py"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from rag import config
from rag.chunking import STRATEGIES
from rag.embeddings import EMBEDDERS
from rag.llm import get_llm, ollama_models
from rag.loaders import list_documents, load_any
from rag.pipeline import RAGPipeline, RAGSettings

SAMPLES = Path(__file__).parent / "sample_docs"

st.set_page_config(page_title="Auto-Document Reader", page_icon="📚", layout="wide")
st.title("📚 Auto-Document Reader")
st.caption("Ask questions about your documents. Answers are grounded in retrieved passages, with sources.")

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("🧠 Model")
    provider = st.radio("Answer model", ["Local (Ollama)", "Cloud (OpenAI)"], help="Local keeps all data on your machine.")
    llm_kw: dict = {}
    if provider.startswith("Local"):
        installed = ollama_models()
        default = config.OLLAMA_CHAT_MODEL
        options = installed or [default]
        idx = options.index(default) if default in options else 0
        llm_kw["model"] = st.selectbox("Ollama model", options, index=idx)
        if not installed:
            st.warning("Ollama not detected. Start it with `ollama serve` and `ollama pull qwen2.5:3b`.")
        llm_provider = "ollama"
    else:
        key = st.text_input("OpenAI API key", value=config.OPENAI_API_KEY, type="password")
        llm_kw.update(api_key=key, model=st.text_input("Chat model", config.OPENAI_CHAT_MODEL))
        llm_provider = "openai"

    st.header("🔎 Retrieval")
    embedder = st.selectbox("Embeddings", EMBEDDERS, help=(
        "minilm: local ONNX model, good default (one-time ~80 MB download)\n\n"
        "ollama: local, uses OLLAMA_EMBED_MODEL (e.g. nomic-embed-text)\n\n"
        "openai: cloud text-embedding-3-small\n\n"
        "hash: offline lexical fallback, no downloads"))
    emb_kw: dict = {}
    if embedder == "openai":
        emb_kw["api_key"] = llm_kw.get("api_key") or config.OPENAI_API_KEY
    elif embedder == "ollama":
        emb_kw["model"] = st.text_input("Ollama embedding model", config.OLLAMA_EMBED_MODEL)
    strategy = st.selectbox("Chunking", STRATEGIES, index=STRATEGIES.index(config.DEFAULT_STRATEGY))
    size = st.slider("Chunk size (chars)", 200, 2000, config.DEFAULT_CHUNK_SIZE, 50)
    overlap = st.slider("Overlap (chars)", 0, 500, config.DEFAULT_CHUNK_OVERLAP, 10)
    top_k = st.slider("Top-k passages", 1, 10, config.DEFAULT_TOP_K)
    min_score = st.slider("Min similarity", 0.0, 0.9, 0.0, 0.05, help="Drop weak matches (reduces off-topic answers).")

# ----------------------------------------------------------------- pipeline (rebuilt when settings change)
settings = RAGSettings(embedder, emb_kw, strategy, size, min(overlap, size - 1), top_k, min_score)
sig = (embedder, str(emb_kw), strategy, size, overlap)
if st.session_state.get("sig") != sig:
    try:
        with st.spinner("Preparing index for these settings…"):
            st.session_state.pipe = RAGPipeline(settings)
            st.session_state.pipe.sync_index()
        st.session_state.sig = sig
    except Exception as e:  # missing key, no network for model download, etc.
        st.error(f"Could not initialise '{embedder}' embeddings: {e}")
        st.stop()
pipe: RAGPipeline = st.session_state.pipe
pipe.s.top_k, pipe.s.min_score = top_k, min_score

# ----------------------------------------------------------------- documents panel
left, right = st.columns([1, 2], gap="large")
with left:
    st.subheader("Documents")
    files = st.file_uploader("Upload PDF / TXT / MD / DOCX", type=["pdf", "txt", "md", "docx"], accept_multiple_files=True)
    url = st.text_input("…or add a web page URL", placeholder="https://en.wikipedia.org/wiki/…")
    c1, c2 = st.columns(2)
    add_clicked = c1.button("➕ Add", use_container_width=True)
    sample_clicked = c2.button("📂 Load samples", use_container_width=True)

    if add_clicked:
        existing = {d.source for d in list_documents()}
        jobs = [(f.name, f.getvalue()) for f in files or [] if f.name not in existing]
        if url and url not in existing:
            jobs.append((url, None))
        for name, data in jobs:
            try:
                with st.spinner(f"Indexing {name}…"):
                    n = pipe.add_document(load_any(name, data))
                st.success(f"{name}: {n} chunks")
            except Exception as e:
                st.error(f"{name}: {e}")
    if sample_clicked:
        existing = {d.source for d in list_documents()}
        for p in sorted(SAMPLES.iterdir()):
            if p.name not in existing:
                with st.spinner(f"Indexing {p.name}…"):
                    pipe.add_document(load_any(str(p)))
        st.rerun()

    docs = list_documents()
    st.markdown(f"**{len(docs)} document(s)** · {pipe.store.count()} chunks in current index")
    selected = []
    for d in docs:
        row = st.columns([6, 1])
        if row[0].checkbox(f"{d.name}  ·  {d.kind}", value=True, key=f"sel_{d.doc_id}"):
            selected.append(d.doc_id)
        if row[1].button("🗑", key=f"del_{d.doc_id}", help="Remove"):
            pipe.remove_document(d.doc_id)
            st.rerun()
    st.caption("Ticked documents are searched. Untick to narrow the scope; tick all for cross-document questions.")
    if st.button("🧹 Clear chat"):
        st.session_state.history = []
        st.rerun()

# ----------------------------------------------------------------- chat
def render_sources(hits, query=None):
    if query:
        st.caption(f"🔁 Search query used: *{query}*")
    for i, h in enumerate(hits, 1):
        with st.expander(f"[{i}] {h['doc_name']} · {h['locator']} · similarity {h['score']:.2f}"):
            st.write(h["text"])

with right:
    st.subheader("Chat")
    st.session_state.setdefault("history", [])
    for m in st.session_state.history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("sources"):
                render_sources(m["sources"], m.get("query"))

    q = st.chat_input("Ask something about your documents…" if docs else "Upload or load documents first")
    if q:
        if not docs:
            st.warning("Add at least one document first.")
            st.stop()
        st.session_state.history.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            try:
                llm = get_llm(llm_provider, **llm_kw)
                plain = [{"role": m["role"], "content": m["content"]} for m in st.session_state.history[:-1]]
                query, hits, stream = pipe.ask_stream(q, llm, plain, selected or None)
                answer = st.write_stream(stream)
                render_sources(hits, query if query != q else None)
                st.session_state.history.append({"role": "assistant", "content": answer, "sources": hits,
                                                 "query": query if query != q else None})
            except Exception as e:
                st.error(str(e))
