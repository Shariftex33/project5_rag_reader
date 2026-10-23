"""Central configuration (env vars + defaults)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is optional
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", ROOT / "data"))
DOC_STORE = DATA_DIR / "docs"          # parsed documents (JSON) - source of truth
CHROMA_DIR = DATA_DIR / "chroma"       # vector index
DOC_STORE.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Defaults for chunking / retrieval
DEFAULT_CHUNK_SIZE = 800       # characters
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_STRATEGY = "recursive"
DEFAULT_TOP_K = 5
