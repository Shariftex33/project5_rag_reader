"""Pre-load the sample docs into the index (optional; the UI also has a 'Load samples' button).
   python scripts/ingest_samples.py --embedder minilm"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.loaders import load_any
from rag.pipeline import RAGPipeline, RAGSettings

ap = argparse.ArgumentParser()
ap.add_argument("--embedder", default="minilm", choices=["minilm", "ollama", "openai", "hash"])
a = ap.parse_args()
pipe = RAGPipeline(RAGSettings(embedder=a.embedder))
for p in sorted((Path(__file__).resolve().parent.parent / "sample_docs").iterdir()):
    print(f"{p.name}: {pipe.add_document(load_any(str(p)))} chunks")
