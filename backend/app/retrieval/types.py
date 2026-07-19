"""Pydantic models shared by retrieval and agent tools."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

MAX_PASSAGE_EXCERPT_CHARS = 800
MAX_AGENT_OUTPUT_CHARS = 12_000


class SearchFilters(BaseModel):
    """Filters applied to both semantic and full-text retrieval queries.

    Indian-market filters:
        tickers:              One or more NSE symbols (replaces single ``ticker``).
        financial_year:       Exact FY string, e.g. "FY2025" or "Q3FY24".
        financial_year_range: Inclusive range, e.g. ("FY2022", "FY2025").
        document_types:       List of DocumentType values to restrict results.
        industry:             Free-text industry label.

    Legacy SEC filters (kept for backward compat with existing corpus):
        ticker:       Single ticker — mapped to ``tickers`` internally.
        fiscal_years: List of integer years — mapped to ``financial_year`` filtering.
        form:         SEC form type (10-K, 10-Q) — mapped to ``document_types``.
    """

    # --- Indian-market filters ---
    tickers: list[str] | None = None
    financial_year: str | None = None
    financial_year_range: tuple[str, str] | None = None  # (from_fy, to_fy) inclusive
    document_types: list[str] | None = None
    industry: str | None = None

    # --- Legacy SEC filters ---
    ticker: str | None = None          # convenience alias; merged into tickers in queries
    fiscal_years: list[int] | None = None
    form: str | None = None


class RankedChunkHit(BaseModel):
    chunk_id: UUID
    rank: int
    score: float | None = None


class RetrievedPassage(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    page: str | None
    section: str | None
    fusion_score: float
    ticker: str
    company_name: str | None
    # Indian-market fields
    document_type: str | None = None   # e.g. "annual_report"
    financial_year: str | None = None  # e.g. "FY2025"
    filing_date: date | None = None
    # Legacy SEC fields (kept so existing passages still work)
    form: str | None = None
    fiscal_year: int | None = None
    accession_number: str | None = None
    neighbors: list[RetrievedPassage] = Field(default_factory=list)


def _format_one_passage(passage: RetrievedPassage, *, include_neighbors: bool) -> str:
    # Prefer Indian financial_year; fall back to legacy fiscal_year or filing_date year
    fy = passage.financial_year or (
        f"FY{passage.fiscal_year}" if passage.fiscal_year else (
            f"FY{passage.filing_date.year}" if passage.filing_date else "FY?"
        )
    )
    doc_type = passage.document_type or passage.form or "document"
    page = f" p.{passage.page}" if passage.page else ""
    section = f" ({passage.section})" if passage.section else ""
    excerpt = passage.text.strip()
    if len(excerpt) > MAX_PASSAGE_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_PASSAGE_EXCERPT_CHARS] + "..."
    header = (
        f"{passage.ticker} {doc_type} {fy}{page}{section} "
        f"[{passage.chunk_id}]: {excerpt}"
    )
    lines = [header]
    if include_neighbors:
        for neighbor in passage.neighbors:
            neighbor_excerpt = neighbor.text.strip()
            if len(neighbor_excerpt) > MAX_PASSAGE_EXCERPT_CHARS:
                neighbor_excerpt = neighbor_excerpt[:MAX_PASSAGE_EXCERPT_CHARS] + "..."
            lines.append(
                f"  neighbor idx={neighbor.chunk_index} [{neighbor.chunk_id}]: {neighbor_excerpt}"
            )
    return "\n".join(lines)


def format_passages_for_agent(passages: list[RetrievedPassage]) -> str:
    """Bounded, grep-style text for PydanticAI tool responses."""
    if not passages:
        return "No matching passages found in the corporate filing corpus."

    blocks = [_format_one_passage(p, include_neighbors=True) for p in passages]
    output = "\n\n".join(blocks)
    if len(output) > MAX_AGENT_OUTPUT_CHARS:
        output = (
            output[:MAX_AGENT_OUTPUT_CHARS]
            + f"\n... truncated to {len(passages)} passages."
        )
    return output
