# 📚 Auto-Document Reader (RAG)

Upload PDFs, Word files, text/Markdown files or web pages, then ask questions in natural language.
Answers are generated **only from retrieved passages** and every answer shows the **source chunks**
(file, page/section, similarity score). Works with a **local model (Ollama, e.g. `qwen2.5:3b`)** or a
**cloud model (OpenAI)** - switch in the sidebar.

## Features

| Requirement                 | Implementation                                                                                                              |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| PDF, TXT, DOCX, URLs        | `rag/loaders.py` (pypdf, python-docx, BeautifulSoup); page numbers / headings kept as locators                            |
| Chunking with overlap       | `rag/chunking.py`: `fixed`, `recursive`, `sentence` strategies, size and overlap adjustable in the UI               |
| Embeddings + vector store   | ChromaDB (cosine / HNSW). Embedders:`minilm` (local), `ollama` (local), `openai` (cloud), `hash` (offline fallback) |
| Q&A with source attribution | Numbered context passages,`[1]`-style citations, expandable source cards                                                  |
| Multi-document queries      | One collection across all documents; tick/untick documents to scope the search                                              |
| Conversation mode           | Follow-ups are rewritten into standalone search queries using chat history ("🔁 Search query used")                         |
| Local*and* cloud          | Ollama (default`qwen2.5:3b`) or OpenAI (`gpt-4o-mini`, `text-embedding-3-small`)                                      |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # Windows: copy .env.example .env

# ---- local model (Ollama) ----
ollama pull qwen2.5:3b                                 # answer model
ollama pull nomic-embed-text                           # optional: better local embeddings than hash
ollama serve                                           # if it is not already running

streamlit run app.py
```

Then in the app: sidebar -> **Local (Ollama)** -> click **📂 Load samples** -> ask
*"What is the home office stipend?"*, then the follow-up *"And the internet allowance?"*.

**Cloud:** choose *Cloud (OpenAI)* and paste your key (or set `OPENAI_API_KEY` in `.env`).
Documents are embedded and sent as context to OpenAI in this mode; use Local for private files.

### Choosing embeddings

| Option     | Needs                            | Notes                                                  |
| ---------- | -------------------------------- | ------------------------------------------------------ |
| `minilm` | internet once (~80 MB model)     | best no-setup local semantic option                    |
| `ollama` | `ollama pull nomic-embed-text` | fully local                                            |
| `openai` | API key                          | highest quality, paid                                  |
| `hash`   | nothing                          | lexical fallback; works offline; weaker on paraphrases |

Each (embedder, strategy, size, overlap) combination gets its **own Chroma collection**, so you can change
settings in the sidebar freely; stored documents are re-chunked and re-indexed automatically.

## Project layout

```
app.py                  Streamlit UI
rag/
  config.py             env + defaults
  loaders.py            PDF / TXT / DOCX / URL -> Document (+ JSON persistence)
  chunking.py           fixed / recursive / sentence splitters
  embeddings.py         minilm / ollama / openai / hash
  store.py              ChromaDB wrapper
  llm.py                OllamaLLM, OpenAILLM (streaming)
  pipeline.py           ingest, retrieve, condense follow-ups, grounded answer
sample_docs/            3 samples: .txt, .docx, .pdf  (regenerate: python scripts/make_samples.py)
evaluation/             eval_questions.json, run_eval.py, REPORT.md (auto-generated grid)
EVALUATION_REPORT.md    written analysis of chunking / embedding strategies
presentation/           5-7 minute deck + speaker notes
scripts/                cli.py (terminal chat), ingest_samples.py, make_samples.py
tests/                  offline tests (python tests/test_pipeline.py)
```

## How it works

1. **Ingest** - the file is parsed into sections (page / heading) and saved as JSON in `data/docs/`.
2. **Chunk** - sections are split (default: recursive, 800 chars, 150 overlap); each chunk keeps its doc name and locator.
3. **Embed + store** - chunks are embedded and upserted into ChromaDB with metadata.
4. **Ask** - follow-ups are condensed to a standalone query -> top-k similarity search (optionally filtered to selected docs,
   optional minimum-similarity cut-off) -> prompt with numbered passages.
5. **Answer** - the model must cite `[n]` or reply "I couldn't find that in the uploaded documents." The UI lists the passages used.

## Evaluate

```bash
python evaluation/run_eval.py                                   # offline grid, retrieval metrics only
python evaluation/run_eval.py --embedders hash minilm ollama    # compare embedders
python evaluation/run_eval.py --llm ollama --answers --sizes 600 --strategies sentence   # + answer correctness / groundedness
```

Results: `evaluation/REPORT.md`; interpretation: `EVALUATION_REPORT.md`.

## Tips for qwen2.5:3b

* Keep **Top-k 3-5** and chunk size **<= 800** (context is 4096 tokens).
* If answers drift off-topic, raise **Min similarity** so weak passages are dropped.
* Rewriting follow-ups uses the same model; if it misbehaves, the original question is used as a fallback.

## Troubleshooting

* *"Cannot reach Ollama"* - run `ollama serve`; change `OLLAMA_URL` in `.env` if it is remote.
* *"Model not found"* - `ollama pull qwen2.5:3b` (or pick an installed model in the sidebar).
* *minilm download fails* (offline/proxy) - choose the `hash` or `ollama` embedder.
* *Scanned PDF has no text* - run OCR first (e.g. `ocrmypdf in.pdf out.pdf`).
* Reset everything: delete the `data/` folder.

## Tests

`python tests/test_pipeline.py` (chunk bounds/overlap, all formats load, multi-doc retrieval + scoping, "not found" path, follow-up condensing).
