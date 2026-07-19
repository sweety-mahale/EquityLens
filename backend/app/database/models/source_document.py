from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.models.constants import DocumentType

if TYPE_CHECKING:
    from app.database.models.document_chunk import DocumentChunk
    from app.database.models.document_table import DocumentTable


class SourceDocument(Base, TimestampMixin):
    """Normalized corporate filing stored for chunking, retrieval, and citation.

    Supports both Indian corporate filings (NSE, BSE, company IR) and the
    original SEC filing corpus. SEC-specific columns are nullable for
    backward compatibility with the existing sample corpus.
    """

    __tablename__ = "source_documents"
    __table_args__ = (
        Index("ix_source_documents_ticker_financial_year_doctype", "ticker", "financial_year", "document_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # --- Core fields (used by both Indian and SEC corpora) ---
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Indian-market fields
    document_type: Mapped[str | None] = mapped_column(
        Enum(DocumentType, name="document_type_enum", create_type=False),
        nullable=True,
        comment="Controlled vocab: annual_report, quarterly_results, etc.",
    )
    financial_year: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="e.g. FY2025 or Q3FY24",
    )
    industry: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Free-text sector label, e.g. Information Technology",
    )
    source: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Origin of the document: NSE, BSE, Company IR, etc.",
    )
    storage_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Local or object-storage path to the original file",
    )

    # --- Legacy SEC-specific columns (nullable, kept for existing corpus) ---
    cik: Mapped[str | None] = mapped_column(String(10), nullable=True)
    form: Mapped[str | None] = mapped_column(String(16), nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    accession_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_document: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_content: Mapped[str | None] = mapped_column(Text)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    tables: Mapped[list[DocumentTable]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
