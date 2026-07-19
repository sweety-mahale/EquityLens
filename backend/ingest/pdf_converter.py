"""PDF → page-aware Markdown converter for corporate filings.

Uses pdfplumber for text extraction. Page boundaries are injected as
``<!-- page: N -->`` markers so downstream chunking can preserve page numbers.
Section titles are heuristically detected by font size (when metadata is available).

Usage:
    from pathlib import Path
    from ingest.pdf_converter import pdf_to_markdown

    markdown = pdf_to_markdown(Path("reliance_fy2025.pdf"))
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    import pdfplumber
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False

# Words-per-line threshold to treat a short bold/large line as a section title
_TITLE_MAX_WORDS = 10
# Minimum character content for a page to be kept (skip blank/image-only pages)
_MIN_PAGE_CHARS = 20
# If pdfplumber reports a font size above this, treat the line as a heading
_HEADING_SIZE_THRESHOLD = 13.0


def pdf_to_markdown(path: Path, *, preserve_pages: bool = True) -> str:
    """Convert a PDF file to Markdown with optional page markers.

    Args:
        path:           Absolute path to the PDF file.
        preserve_pages: If True (default), inject ``<!-- page: N -->`` markers
                        before each page's text. Downstream chunking uses these
                        to populate the ``page`` metadata field.

    Returns:
        Markdown string representing the full document.

    Raises:
        ImportError: If pdfplumber is not installed.
        FileNotFoundError: If the PDF file does not exist.
    """
    if not _PDFPLUMBER_AVAILABLE:
        raise ImportError(
            "pdfplumber is required for PDF conversion. "
            "Install it with: uv add pdfplumber --extra ingest"
        )

    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    sections: list[str] = []

    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = _extract_page_text(page)
            if not text or len(text) < _MIN_PAGE_CHARS:
                continue

            page_section = f"<!-- page: {page_num} -->\n\n{text}"
            sections.append(page_section)

    return "\n\n".join(sections)


def _extract_page_text(page) -> str:
    """Extract text from a single pdfplumber page with heading detection."""
    # Try to get words with font-size metadata for heading detection
    try:
        words = page.extract_words(extra_attrs=["size"])
        if words:
            return _words_to_markdown(words)
    except Exception:
        pass

    # Fallback: plain text extraction
    return (page.extract_text() or "").strip()


def _words_to_markdown(words: list[dict]) -> str:
    """Group words into lines, detect headings by font size."""
    if not words:
        return ""

    # Group by top-coordinate (same line)
    lines_by_top: dict[float, list[dict]] = {}
    for word in words:
        top = round(word.get("top", 0), 1)
        lines_by_top.setdefault(top, []).append(word)

    lines: list[str] = []
    for top in sorted(lines_by_top):
        line_words = sorted(lines_by_top[top], key=lambda w: w.get("x0", 0))
        line_text = " ".join(w["text"] for w in line_words).strip()
        if not line_text:
            continue

        # Detect heading: large font, short line
        max_size = max((w.get("size") or 0) for w in line_words)
        word_count = len(line_text.split())
        if max_size >= _HEADING_SIZE_THRESHOLD and word_count <= _TITLE_MAX_WORDS:
            lines.append(f"## {line_text}")
        else:
            lines.append(line_text)

    return "\n".join(lines)
