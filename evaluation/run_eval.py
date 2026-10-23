"""Compare chunking strategies / sizes / embedders on the sample questions.

Retrieval metrics (no LLM needed):
  Hit@k   - fraction of questions where a retrieved chunk contains ALL gold phrases
  MRR     - mean of 1/rank of the first chunk that does
Faithfulness / correctness (needs an LLM, optional --llm ollama|openai):
  Answer-correct - the answer text contains the expected keywords
  Grounded       - LLM-as-judge: is every claim supported by the retrieved context? (yes/no)

Usage:
  python evaluation/run_eval.py                              # offline 'hash' embedder, retrieval only
  python evaluation/run_eval.py --embedders hash minilm      # add local MiniLM
  python evaluation/run_eval.py --embedders ollama openai --llm ollama --answers
Writes evaluation/results.json and evaluation/REPORT.md
"""
from __future__ import annotations

import argparse, itertools, json, os, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("RAG_DATA_DIR", tempfile.mkdtemp(prefix="rag_eval_"))   # keep eval out of the app's index

from rag.loaders import load_any                      # noqa: E402
from rag.pipeline import RAGPipeline, RAGSettings     # noqa: E402
from rag.llm import get_llm                           # noqa: E402

QUESTIONS = json.loads((ROOT / "evaluation" / "eval_questions.json").read_text())
DOCS = [load_any(str(p)) for p in sorted((ROOT / "sample_docs").iterdir())]


def hit_rank(hits, gold):
    for i, h in enumerate(hits, 1):
        if all(g.lower() in h["text"].lower() for g in gold):
            return i
    return None


JUDGE = ("You are a strict fact-checker. CONTEXT:\n{ctx}\n\nANSWER:\n{ans}\n\n"
         "Is every factual claim in the ANSWER supported by the CONTEXT? Reply with only YES or NO.")


def evaluate(cfg: dict, k: int, llm=None, answers=False):
    s = RAGSettings(embedder=cfg["embedder"], strategy=cfg["strategy"], chunk_size=cfg["size"],
                    chunk_overlap=cfg["overlap"], top_k=k, embedder_kwargs=cfg.get("kw", {}))
    p = RAGPipeline(s)
    t0 = time.time()
    n_chunks = sum(p.add_document(d) for d in DOCS)
    index_s = time.time() - t0
    ranks, correct, grounded, per_q = [], 0, 0, []
    for item in QUESTIONS:
        hits = p.retrieve(item["q"])
        r = hit_rank(hits, item["gold"])
        ranks.append(r)
        rec = {"q": item["q"], "rank": r}
        if answers and llm:
            ans = p.ask(item["q"], llm).text
            ok = any(a.lower() in ans.lower() for a in item["answer"])
            correct += ok
            ctx = p.build_context(p.retrieve(item["q"]))
            verdict = llm.chat([{"role": "user", "content": JUDGE.format(ctx=ctx, ans=ans)}], 0.0)
            grounded += verdict.strip().upper().startswith("YES")
            rec.update(answer=ans, correct=bool(ok))
        per_q.append(rec)
    n = len(QUESTIONS)
    texts = p.store.col.get()["documents"]
    out = {**cfg, "k": k, "chunks": n_chunks, "avg_chunk_chars": round(sum(map(len, texts)) / max(1, len(texts))),
           "hit_at_k": round(sum(r is not None for r in ranks) / n, 3),
           "mrr": round(sum(1 / r for r in ranks if r) / n, 3), "index_s": round(index_s, 2), "per_q": per_q}
    if answers and llm:
        out.update(answer_correct=round(correct / n, 3), grounded=round(grounded / n, 3))
    return out


def write_report(results, args):
    L = ["# Evaluation report", "",
         f"Questions: **{len(QUESTIONS)}** over 3 documents (PDF, DOCX, TXT) - top-k = **{args.k}**.", "",
         "Hit@k = a retrieved chunk contains the gold evidence; MRR = mean reciprocal rank of the first such chunk.", ""]
    has_ans = any("answer_correct" in r for r in results)
    hdr = "| Embedder | Strategy | Size | Overlap | Chunks | Avg chars | Hit@k | MRR | Index s |" + (" Answer-correct | Grounded |" if has_ans else "")
    L += [hdr, "|" + "---|" * (hdr.count("|") - 1)]
    for r in sorted(results, key=lambda r: (r["embedder"], -r["mrr"])):
        row = f"| {r['embedder']} | {r['strategy']} | {r['size']} | {r['overlap']} | {r['chunks']} | {r['avg_chunk_chars']} | {r['hit_at_k']} | {r['mrr']} | {r['index_s']} |"
        if has_ans:
            row += f" {r.get('answer_correct', '-')} | {r.get('grounded', '-')} |"
        L.append(row)
    best = max(results, key=lambda r: (r["mrr"], r["hit_at_k"]))
    L += ["", f"**Best configuration in this run:** {best['embedder']} + {best['strategy']} "
              f"(size {best['size']}, overlap {best['overlap']}) - Hit@{args.k} {best['hit_at_k']}, MRR {best['mrr']}.", ""]
    missed = [q["q"] for q in best["per_q"] if q["rank"] is None]
    L.append("Questions the best configuration still missed: " + ("; ".join(missed) if missed else "none") + ".")
    (ROOT / "evaluation" / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedders", nargs="+", default=["hash"])
    ap.add_argument("--strategies", nargs="+", default=["fixed", "recursive", "sentence"])
    ap.add_argument("--sizes", nargs="+", type=int, default=[300, 600, 1000])
    ap.add_argument("--overlaps", nargs="+", type=int, default=[0, 100])
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--llm", choices=["ollama", "openai"], help="LLM for answer-level metrics")
    ap.add_argument("--answers", action="store_true", help="also grade generated answers (slow with small local models)")
    args = ap.parse_args()
    llm = get_llm(args.llm) if args.llm else None
    results = []
    for emb, strat, size, ov in itertools.product(args.embedders, args.strategies, args.sizes, args.overlaps):
        if ov >= size:
            continue
        cfg = {"embedder": emb, "strategy": strat, "size": size, "overlap": ov}
        r = evaluate(cfg, args.k, llm, args.answers)
        results.append(r)
        print(f"{emb:7} {strat:9} size={size:<5} ov={ov:<4} chunks={r['chunks']:<4} Hit@{args.k}={r['hit_at_k']:<5} MRR={r['mrr']}")
    (ROOT / "evaluation" / "results.json").write_text(json.dumps(results, indent=1))
    write_report(results, args)
    print("\nWrote evaluation/REPORT.md")
