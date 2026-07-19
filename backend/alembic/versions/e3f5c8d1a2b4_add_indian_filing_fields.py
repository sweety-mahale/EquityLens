"""add Indian financial research platform fields

Adds columns for Indian corporate filing metadata to source_documents.
SEC-specific columns (cik, accession_number, form, primary_document,
source_url) are made nullable so existing rows remain valid.

Revision ID: e3f5c8d1a2b4
Revises: d2e4b7a9c1f3
Create Date: 2026-07-18 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e3f5c8d1a2b4"
down_revision: Union[str, Sequence[str], None] = "d2e4b7a9c1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the document_type enum type in Postgres
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_type_enum') THEN
                CREATE TYPE document_type_enum AS ENUM (
                    'annual_report',
                    'quarterly_results',
                    'investor_presentation',
                    'earnings_call',
                    'corporate_announcement'
                );
            END IF;
        END$$;
        """
    )

    # 2. Add new Indian-market columns to source_documents
    op.add_column(
        "source_documents",
        sa.Column(
            "document_type",
            sa.Enum(
                "annual_report",
                "quarterly_results",
                "investor_presentation",
                "earnings_call",
                "corporate_announcement",
                name="document_type_enum",
                create_type=False,
            ),
            nullable=True,
            comment="Controlled vocab for corporate filing type",
        ),
    )
    op.add_column(
        "source_documents",
        sa.Column(
            "financial_year",
            sa.String(16),
            nullable=True,
            comment="e.g. FY2025 or Q3FY24",
        ),
    )
    op.add_column(
        "source_documents",
        sa.Column(
            "industry",
            sa.String(128),
            nullable=True,
            comment="Free-text sector, e.g. Information Technology",
        ),
    )
    op.add_column(
        "source_documents",
        sa.Column(
            "source",
            sa.String(64),
            nullable=True,
            comment="Document origin: NSE, BSE, Company IR, etc.",
        ),
    )
    op.add_column(
        "source_documents",
        sa.Column(
            "storage_path",
            sa.Text(),
            nullable=True,
            comment="Local or object-storage path to original file",
        ),
    )

    # 3. Make legacy SEC-specific columns nullable (non-breaking)
    op.alter_column("source_documents", "cik", nullable=True)
    op.alter_column("source_documents", "form", nullable=True)
    op.alter_column("source_documents", "accession_number", nullable=True)
    op.alter_column("source_documents", "primary_document", nullable=True)
    op.alter_column("source_documents", "source_url", nullable=True)

    # 4. Drop the old SEC-centric unique constraint on accession_number
    #    (accession_number is now nullable so uniqueness is meaningless for NULLs,
    #    and new documents won't have accession numbers at all)
    op.drop_constraint(
        "uq_source_documents_accession_number",
        "source_documents",
        type_="unique",
    )

    # 5. Drop old index, create new India-centric composite index
    op.drop_index("ix_source_documents_ticker_fiscal_year", table_name="source_documents")
    op.create_index(
        "ix_source_documents_ticker_financial_year_doctype",
        "source_documents",
        ["ticker", "financial_year", "document_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_documents_ticker_financial_year_doctype",
        table_name="source_documents",
    )
    op.create_index(
        "ix_source_documents_ticker_fiscal_year",
        "source_documents",
        ["ticker", "fiscal_year"],
    )
    op.create_unique_constraint(
        "uq_source_documents_accession_number",
        "source_documents",
        ["accession_number"],
    )

    # Restore NOT NULL constraints on SEC columns
    op.alter_column("source_documents", "source_url", nullable=False)
    op.alter_column("source_documents", "primary_document", nullable=False)
    op.alter_column("source_documents", "accession_number", nullable=False)
    op.alter_column("source_documents", "form", nullable=False)
    op.alter_column("source_documents", "cik", nullable=False)

    op.drop_index(
        "ix_source_documents_ticker_financial_year_doctype",
        table_name="source_documents",
    )
    op.drop_column("source_documents", "storage_path")
    op.drop_column("source_documents", "source")
    op.drop_column("source_documents", "industry")
    op.drop_column("source_documents", "financial_year")
    op.drop_column("source_documents", "document_type")

    op.execute("DROP TYPE IF EXISTS document_type_enum")
