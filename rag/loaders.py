"""Document loaders: PDF, TXT/MD, DOCX and web URLs -> a list of text 'sections'.

Every loader returns a `Document`: a name, a source and a list of
(`locator`, `text`) sections. A locator is a page number for PDFs, a heading
or paragraph block for DOCX, and 1 for plain text / web pages. The locator is
carried through chunking so the UI can say "page 3 of report.pdf".
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import BinaryIO

from .config import DOC_STORE


@dataclass
class Document:
    name: str
    source: str                       # filename or URL
    kind: str                         # pdf | txt | docx | web
    sections: list[tuple[str, str]] = field(default_factory=list)  # (locator, text)
    doc_id: str = ""

    def __post_init__(self):
        if not self.doc_id:
            h = hashlib.sha1((self.source + "".join(t for _, t in self.sections)).encode("utf-8", "ignore"))
            self.doc_id = h.hexdigest()[:12]

    @property
    def n_chars(self) -> int:
        return sum(len(t) for _, t in self.sections)


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ----------------------------------------------------------------- loaders
def load_pdf(data: bytes, name: str) -> Document:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    sections = []
    for i, page in enumerate(reader.pages, start=1):
        txt = _clean(page.extract_text() or "")
        if txt:
            sections.append((f"p.{i}", txt))
    if not sections:
        raise ValueError(f"No extractable text in {name} (scanned PDF? try OCR first).")
    return Document(name=name, source=name, kind="pdf", sections=sections)


def load_txt(data: bytes, name: str) -> Document:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return Document(name=name, source=name, kind="txt", sections=[("1", _clean(text))])


def load_docx(data: bytes, name: str) -> Document:
    from docx import Document as Docx
    d = Docx(io.BytesIO(data))
    sections, heading, buf = [], "Intro", []

    def flush():
        if buf:
            sections.append((heading, _clean("\n".join(buf))))
            buf.clear()

    for p in d.paragraphs:
        if not p.text.strip():
            continue
        if p.style is not None and p.style.name.lower().startswith("heading"):
            flush()
            heading = p.text.strip()
        buf.append(p.text)
    flush()
    # tables -> text rows
    for t_i, table in enumerate(d.tables, start=1):
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in table.rows]
        sections.append((f"table {t_i}", "\n".join(rows)))
    return Document(name=name, source=name, kind="docx", sections=sections)


def load_url(url: str) -> Document:
    import requests
    from bs4 import BeautifulSoup
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (RAG-Reader)"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else url)
    root = soup.find("article") or soup.find("main") or soup.body or soup
    text = _clean(root.get_text("\n"))
    if not text:
        raise ValueError(f"No readable text found at {url}")
    return Document(name=title[:80], source=url, kind="web", sections=[("web", text)])


def load_any(name_or_url: str, data: bytes | None = None) -> Document:
    """Dispatch on extension / URL."""
    if name_or_url.lower().startswith(("http://", "https://")):
        return load_url(name_or_url)
    ext = Path(name_or_url).suffix.lower()
    if data is None:
        data = Path(name_or_url).read_bytes()
    name = Path(name_or_url).name
    if ext == ".pdf":
        return load_pdf(data, name)
    if ext in (".txt", ".md", ".text"):
        return load_txt(data, name)
    if ext == ".docx":
        return load_docx(data, name)
    raise ValueError(f"Unsupported file type: {ext or name_or_url}")


# ----------------------------------------------------------------- persistence
def save_document(doc: Document) -> None:
    (DOC_STORE / f"{doc.doc_id}.json").write_text(json.dumps(asdict(doc), ensure_ascii=False), encoding="utf-8")


def list_documents() -> list[Document]:
    docs = []
    for p in sorted(DOC_STORE.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        d["sections"] = [tuple(s) for s in d["sections"]]
        docs.append(Document(**d))
    return docs


def delete_document(doc_id: str) -> None:
    p = DOC_STORE / f"{doc_id}.json"
    if p.exists():
        p.unlink()
