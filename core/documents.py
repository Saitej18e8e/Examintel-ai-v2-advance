"""Reading exam papers: PDF text extraction, size budgeting and keyword search."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pdfplumber


@dataclass
class Paper:
    name: str
    pages: List[str] = field(default_factory=list)
    used_ocr_fallback: bool = False

    @property
    def text(self) -> str:
        return "\n".join(self.pages)


def load_paper(name: str, data: bytes, llm=None) -> Paper:
    """Extract text page by page. If the PDF has no selectable text and an LLM is
    given, let Gemini read the PDF directly (handles scanned papers)."""
    pages: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                pages.append((page.extract_text() or "").strip())
    except Exception:  # corrupted or encrypted PDF
        pages = []

    if any(p for p in pages):
        return Paper(name=name, pages=pages)

    if llm is not None:
        text = llm.transcribe_pdf(data).strip()
        if text:
            return Paper(name=name, pages=[text], used_ocr_fallback=True)
    return Paper(name=name, pages=[])


def budget_texts(papers: List[Paper], max_chars: int = 120_000) -> Tuple[Dict[str, str], bool]:
    """Give every paper an equal share of the prompt budget so one long paper
    cannot push the others out. Returns (texts, was_truncated)."""
    usable = [p for p in papers if p.text.strip()]
    if not usable:
        return {}, False
    share = max_chars // len(usable)
    out: Dict[str, str] = {}
    truncated = False
    for paper in usable:
        text = paper.text
        if len(text) > share:
            text = text[:share]
            truncated = True
        out[paper.name] = text
    return out, truncated


_WORD = re.compile(r"[a-z0-9]+")


def search_pages(papers: List[Paper], query: str, limit: int = 3, snippet: int = 450) -> List[dict]:
    """Rank pages by how many query words they contain (simple keyword search)."""
    words = set(_WORD.findall(query.lower()))
    if not words:
        return []
    scored = []
    for paper in papers:
        for number, page in enumerate(paper.pages, start=1):
            tokens = _WORD.findall(page.lower())
            if not tokens:
                continue
            hits = sum(1 for t in tokens if t in words)
            if hits:
                scored.append((hits, paper.name, number, page))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [
        {"paper": name, "page": number, "matches": hits, "snippet": page[:snippet]}
        for hits, name, number, page in scored[:limit]
    ]
