"""PDF → page-aware Markdown converter for corporate filings.

Uses pdfplumber with hybrid text and table extraction:
- Detects financial tables via layout bounding boxes and serializes them to Markdown tables.
- Filters out table bounding boxes when extracting paragraph text to eliminate duplicate text.
- Sanitizes non-standard embedded font artifacts (e.g. CID font mappings).
- Injects ``<!-- page: N -->`` markers so downstream chunking can preserve page numbers.
- Detects section titles heuristically by font size and formatting.

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


def clean_text(text: str) -> str:
    """Remove CID font encoding artifacts and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r"\(cid:\d+\)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def format_markdown_table(rows: list[list[str | None]]) -> str:
    """Format a 2D list of table cells into a Markdown table."""
    cleaned_rows: list[list[str]] = []
    for row in rows:
        if not row:
            continue
        cleaned = [clean_text(c or "") for c in row]
        if any(cleaned):
            cleaned_rows.append(cleaned)

    if not cleaned_rows:
        return ""

    ncols = max(len(r) for r in cleaned_rows)
    if ncols < 2:
        return ""  # Not a meaningful table if single column

    for r in cleaned_rows:
        while len(r) < ncols:
            r.append("")

    header = cleaned_rows[0]
    sep = ["---"] * ncols
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for r in cleaned_rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def _is_inside_tables(
    bbox: tuple[float, float, float, float],
    table_bboxes: list[tuple[float, float, float, float]],
) -> bool:
    """Check if a bounding box overlaps with any table bounding boxes."""
    x0, top, x1, bottom = bbox
    for tx0, ttop, tx1, tbottom in table_bboxes:
        if not (x1 <= tx0 or x0 >= tx1 or bottom <= ttop or top >= tbottom):
            return True
    return False


def pdf_to_markdown(path: Path, *, preserve_pages: bool = True) -> str:
    """Convert a PDF file to Markdown with page markers and structured tables.

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
            text = _extract_page_markdown(page)
            if not text or len(text) < _MIN_PAGE_CHARS:
                continue

            if preserve_pages:
                page_section = f"<!-- page: {page_num} -->\n\n{text}"
            else:
                page_section = text
            sections.append(page_section)

    return "\n\n".join(sections)


def _extract_page_markdown(page) -> str:
    """Extract text and tables from a single page in reading order."""
    tables = page.find_tables()
    table_bboxes: list[tuple[float, float, float, float]] = []
    extracted_tables: list[tuple[float, str]] = []

    for t in tables:
        md = format_markdown_table(t.extract())
        if md:
            table_bboxes.append(t.bbox)
            extracted_tables.append((t.bbox[1], md))  # (top, markdown_table_str)

    # Extract words outside table bounding boxes to prevent duplicate text
    try:
        words = page.extract_words(extra_attrs=["size"])
    except Exception:
        words = []

    non_table_words = [
        w for w in words
        if not _is_inside_tables((w["x0"], w["top"], w["x1"], w["bottom"]), table_bboxes)
    ]

    # Group non-table words by line (vertical coordinate)
    lines_by_top: dict[float, list[dict]] = {}
    for w in non_table_words:
        top = round(w.get("top", 0), 1)
        lines_by_top.setdefault(top, []).append(w)

    page_elements: list[tuple[float, str]] = []

    for top in sorted(lines_by_top):
        lw = sorted(lines_by_top[top], key=lambda w: w.get("x0", 0))
        txt = clean_text(" ".join(w["text"] for w in lw))
        if not txt:
            continue
        max_size = max((w.get("size") or 0) for w in lw)
        if max_size >= _HEADING_SIZE_THRESHOLD and len(txt.split()) <= _TITLE_MAX_WORDS:
            page_elements.append((top, f"## {txt}"))
        else:
            page_elements.append((top, txt))

    # Add extracted tables
    for top, tbl_md in extracted_tables:
        page_elements.append((top, tbl_md))

    # Sort all elements (headings, text lines, tables) in natural vertical reading order
    page_elements.sort(key=lambda elem: elem[0])

    # Merge consecutive regular text lines into paragraphs
    blocks: list[str] = []
    current_para: list[str] = []
    for _, text in page_elements:
        if text.startswith("## ") or text.startswith("|"):
            if current_para:
                blocks.append("\n".join(current_para))
                current_para = []
            blocks.append(text)
        else:
            current_para.append(text)
    if current_para:
        blocks.append("\n".join(current_para))

    # Fallback to plain text if word extraction yielded nothing
    if not blocks:
        raw_text = clean_text(page.extract_text() or "")
        return raw_text

    return "\n\n".join(blocks)
