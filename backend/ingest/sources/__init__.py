"""Document source abstraction for the India Financials Copilot ingestion pipeline.

Every document source implements the `DocumentSource` Protocol. The ingestion
pipeline only depends on this protocol, so new sources (BSE, SEBI, RBI, IPO
prospectuses) can be plugged in without touching any RAG code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class DocumentRecord:
    """Source-agnostic representation of a single corporate document.

    All metadata fields here map 1-to-1 to ``SourceDocument`` columns.
    """

    ticker: str
    company_name: str
    filing_date: date
    document_type: str  # One of DocumentType enum values
    financial_year: str  # e.g. "FY2025" or "Q3FY24"
    source: str  # "NSE", "BSE", "Company IR", etc.
    storage_path: Path  # Absolute path to the local file (PDF or Markdown)
    industry: str | None = None
    # Derived Markdown content; set by the pipeline after PDF conversion
    markdown_content: str | None = None
    # Extra source-specific metadata stored as JSON
    extra: dict = field(default_factory=dict)


@runtime_checkable
class DocumentSource(Protocol):
    """Protocol that every document source must satisfy.

    Implementations:
    - :class:`~ingest.sources.nse.NseDocumentSource`
    - :class:`~ingest.sources.company_website.CompanyWebsiteSource`
    - :class:`~ingest.sources.local_pdf.LocalPdfSource`
    """

    def fetch_documents(self) -> list[DocumentRecord]:
        """Return a list of document records ready for ingestion.

        Each record must have a valid ``storage_path`` pointing to a PDF or
        Markdown file. The pipeline converts PDFs to Markdown automatically.
        """
        ...
