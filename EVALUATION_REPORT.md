# Evaluation Report: chunking & embedding strategies

## 1. Setup
* **Corpus:** 3 sample documents in different formats - `intro_to_rag.txt`, `remote_work_policy.docx`, `solar_system_guide.pdf` (~7,400 characters of text).
* **Question set:** 18 hand-written questions (`evaluation/eval_questions.json`), 6 per document, each with a *gold phrase* that must appear in the evidence. Several are deliberate paraphrases ("stolen laptop" vs. "lost or stolen equipment") to stress semantic matching.
* **Metrics**
  * **Hit@k** - share of questions where at least one of the top-k chunks contains the gold evidence.
  * **MRR** - mean of 1/rank of the first chunk that contains it (rewards putting the right chunk first).
  * **Answer-correct / Grounded** (optional, `--answers`) - expected keywords in the generated answer, plus an LLM-as-judge check that every claim is supported by the retrieved context.
* **Grid:** 3 strategies x 3 sizes (300 / 600 / 1000 chars) x 2 overlaps (0 / 100 chars), k = 3.

## 2. Results already measured (offline `hash` embedder)
These numbers were produced in the build environment with the dependency-free `hash` embedder (lexical hashing vectors, no downloads). Full grid: `evaluation/REPORT.md` and `evaluation/results.json`.

| Factor | Setting | Mean Hit@3 | Mean MRR |
|---|---|---|---|
| Strategy | fixed | 0.768 | 0.693 |
| | recursive | 0.824 | 0.756 |
| | **sentence** | **0.916** | **0.826** |
| Chunk size | 300 | 0.842 | 0.756 |
| | **600** | **0.852** | **0.772** |
| | 1000 | 0.815 | 0.747 |
| Overlap | 0 | 0.839 | 0.754 |
| | 100 | 0.833 | 0.762 |

Best single configuration: **sentence chunking, 600 chars** - Hit@3 = 0.944, MRR = 0.852. The only question it missed was *"How long do I have to report a stolen laptop?"* - the policy says *"lost or stolen equipment ... within 24 hours"*, so a purely lexical embedder lacks the laptop -> equipment link. This is the kind of miss a semantic embedder is expected to fix.

## 3. Findings
1. **Respecting sentence boundaries helps most.** Fixed windows cut facts in half (the number lands in one chunk, its subject in another) and scored ~15 points lower on Hit@3 than sentence chunking.
2. **Medium chunks win.** 300-char chunks isolate facts but lose context; 1000-char chunks dilute the match with unrelated sentences and give weaker ranking. ~600 is a good default for short factual documents; for long narrative PDFs try 800-1000.
3. **Overlap is nearly neutral here** (+0.008 MRR). The sample documents have short, self-contained paragraphs, so few facts straddle a boundary. Overlap matters most for fixed windows (see `fixed/300`: MRR 0.62 -> 0.67) and for long prose; its cost is ~10-30 % more chunks to embed and store.
4. **Retrieval and faithfulness are separate failure modes.** A correct chunk can still be ignored or paraphrased wrongly by a small model. That is why the prompt forces `[n]` citations and a fixed "couldn't find that" fallback, and why the UI always shows the retrieved passages so users can verify.

## 4. Embedding comparison - run this on your machine
The environment used to build the project cannot download models or call OpenAI, so only the `hash` baseline was measured. Fill in the table by running:

```bash
python evaluation/run_eval.py --embedders hash minilm ollama openai --strategies sentence recursive --sizes 600 --overlaps 100
# add --llm ollama --answers for answer-correctness + groundedness (slow with small local models)
```

| Embedder | Where it runs | Dimensions | Expected behaviour |
|---|---|---|---|
| hash | local, offline | 1024 | lexical only; fast baseline; misses paraphrases |
| minilm (all-MiniLM-L6-v2) | local CPU, ~80 MB | 384 | semantic; good default; short 256-token window |
| ollama / nomic-embed-text | local | 768 | semantic; longer context; needs `ollama pull` |
| openai / text-embedding-3-small | cloud | 1536 | strongest general quality; costs money, sends text to API |

These "expected behaviour" entries are general characteristics, **not measurements from this project**. Replace them with your own results.

## 5. Limitations & next steps
* 18 questions over 3 short documents is a small sample: differences of one question (~0.055 Hit@k) are noise. Add more documents/questions before drawing strong conclusions.
* Gold-phrase matching is strict; a chunk with the right fact but different wording counts as a miss.
* Not implemented, but natural improvements: hybrid BM25 + vector retrieval, a cross-encoder re-ranker, and MMR to diversify results.
* qwen2.5:3b is small: expect good extraction of single facts, weaker multi-hop reasoning. Use `top_k` 3-5 and chunk size <= 800 so the context fits comfortably in its 4k window.
