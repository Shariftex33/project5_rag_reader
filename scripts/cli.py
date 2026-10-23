"""Terminal chat, handy for testing without Streamlit.
   python scripts/cli.py --llm ollama --embedder hash"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.llm import get_llm
from rag.pipeline import RAGPipeline, RAGSettings

ap = argparse.ArgumentParser()
ap.add_argument("--llm", default="ollama", choices=["ollama", "openai"])
ap.add_argument("--embedder", default="minilm", choices=["minilm", "ollama", "openai", "hash"])
a = ap.parse_args()
pipe, llm, hist = RAGPipeline(RAGSettings(embedder=a.embedder)), get_llm(a.llm), []
pipe.sync_index()
print("Ask about your documents (Ctrl-C to quit).")
while True:
    q = input("\nYou: ")
    ans = pipe.ask(q, llm, hist)
    print(f"\nAssistant: {ans.text}\n(search query: {ans.standalone_query})")
    for i, h in enumerate(ans.sources, 1):
        print(f"  [{i}] {h['doc_name']} {h['locator']} sim={h['score']:.2f}")
    hist += [{"role": "user", "content": q}, {"role": "assistant", "content": ans.text}]
