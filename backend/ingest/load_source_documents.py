"""Load corporate filings from any DocumentSource into source_documents.

Supports Indian corporate filings (NSE, Company IR, Local PDFs).
The pipeline is source-agnostic: any class implementing the DocumentSource
protocol can be used.

Usage (NSE):
    uv run python -m ingest.load_source_documents
    # or
    uv run python -m ingest.load_source_documents --source nse

Usage (local PDFs):
    uv run python -m ingest.load_source_documents --source local --dir data/my_pdfs
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import SourceDocument
from ingest.pdf_converter import pdf_to_markdown
from ingest.sources import DocumentRecord

SKIP_EXISTING = True

# ---------------------------------------------------------------------------
# Unique key helpers
# ---------------------------------------------------------------------------

def _india_key(record: DocumentRecord) -> tuple[str, str, str]:
    """Idempotency key for Indian filings."""
    return (record.ticker, record.financial_year, record.document_type)


def _existing_india_docs(session: Session) -> set[tuple[str, str, str]]:
    rows = session.execute(
        select(SourceDocument.ticker, SourceDocument.financial_year, SourceDocument.document_type)
        .where(SourceDocument.document_type.isnot(None))
    ).all()
    return {(r.ticker, r.financial_year, r.document_type) for r in rows}


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------

def load_from_source(records: list[DocumentRecord]) -> dict[str, int]:
    """Persist a list of DocumentRecords into source_documents.

    Converts PDFs to Markdown automatically if the record has no
    ``markdown_content`` yet. Skips existing rows by (ticker, financial_year,
    document_type) key. Commits incrementally per document to prevent connection
    timeouts on large batch ingestions.
    """
    engine = create_engine(
        settings.sqlalchemy_database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    counts = {"inserted": 0, "skipped": 0, "updated": 0}

    with Session(engine) as session:
        existing_keys = _existing_india_docs(session)

    for record in records:
        key = _india_key(record)

        if SKIP_EXISTING and key in existing_keys:
            # Check if metadata (company_name, industry) needs enrichment without re-converting PDF
            try:
                with Session(engine) as session:
                    existing = session.scalar(
                        select(SourceDocument).where(
                            SourceDocument.ticker == record.ticker,
                            SourceDocument.financial_year == record.financial_year,
                            SourceDocument.document_type == record.document_type,
                        )
                    )
                    if existing and (existing.industry is None or existing.company_name == existing.ticker):
                        updated = False
                        if record.company_name and existing.company_name != record.company_name:
                            existing.company_name = record.company_name
                            updated = True
                        if record.industry and existing.industry != record.industry:
                            existing.industry = record.industry
                            updated = True
                        if updated:
                            session.commit()
                            counts["updated"] += 1
                            print(f"Enriched metadata for {record.ticker} {record.financial_year}")
                    else:
                        counts["skipped"] += 1
            except Exception as exc:
                print(f"  [WARN] Metadata update failed for {record.ticker}: {exc}")
                counts["skipped"] += 1
            continue

        # Convert PDF -> Markdown OUTSIDE the database session so DB connection is not held idle during parsing
        markdown = record.markdown_content
        if markdown is None:
            suffix = record.storage_path.suffix.lower()
            if suffix == ".pdf":
                print(f"Converting PDF: {record.storage_path.name}...")
                try:
                    markdown = pdf_to_markdown(record.storage_path)
                except Exception as e:
                    print(f"  [WARN] Failed to convert PDF {record.storage_path.name}: {e}")
                    counts["skipped"] += 1
                    continue
            elif suffix in {".md", ".txt"}:
                markdown = record.storage_path.read_text(encoding="utf-8")
            else:
                print(f"[WARN] Unknown file type {suffix} for {record.storage_path.name}, skipping")
                continue

        fields = {
            "ticker": record.ticker,
            "company_name": record.company_name,
            "filing_date": record.filing_date,
            "document_type": record.document_type,
            "financial_year": record.financial_year,
            "source": record.source,
            "storage_path": str(record.storage_path),
            "industry": record.industry,
            "markdown_content": markdown,
            "ingested_at": datetime.now(UTC),
        }

        # Short, dedicated transaction: insert and commit immediately
        try:
            with Session(engine) as session:
                if key in existing_keys:
                    existing = session.scalar(
                        select(SourceDocument).where(
                            SourceDocument.ticker == record.ticker,
                            SourceDocument.financial_year == record.financial_year,
                            SourceDocument.document_type == record.document_type,
                        )
                    )
                    if existing:
                        for k, v in fields.items():
                            setattr(existing, k, v)
                        session.commit()
                        counts["updated"] += 1
                        print(f"Updated {record.ticker} {record.financial_year}")
                else:
                    session.add(SourceDocument(**fields))
                    session.commit()
                    existing_keys.add(key)
                    counts["inserted"] += 1
                    print(f"Inserted {record.ticker} {record.financial_year} {record.document_type}")
        except Exception as exc:
            print(f"  [ERROR] Database insert failed for {record.ticker} {record.financial_year}: {exc}")

    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["nse", "local"],
        default="nse",
        help="Document source to load (default: nse)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory for --source=local (must contain manifest.json)",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.source == "nse":
        # Default: download from the script's configured companies
        nse_dir = Path(__file__).resolve().parents[2] / "data" / "nse_downloads"
        if not nse_dir.is_dir():
            print(
                f"NSE downloads directory not found: {nse_dir}\n"
                "Run `uv run data/download_nse.py` first."
            )
            return

        # Enumerate all PDFs already downloaded by download_nse.py
        from ingest.sources.local_pdf import LocalPdfSource  # noqa: PLC0415

        source = LocalPdfSource(nse_dir)
        try:
            records = source.fetch_documents()
        except FileNotFoundError:
            # No manifest.json — build records from downloaded PDFs directly
            records = _records_from_downloaded_pdfs(nse_dir)

        result = load_from_source(records)

    elif args.source == "local":
        directory = args.dir
        if directory is None:
            parser.error("--dir is required when --source=local")
        from ingest.sources.local_pdf import LocalPdfSource  # noqa: PLC0415

        source = LocalPdfSource(directory)
        records = source.fetch_documents()
        result = load_from_source(records)

    else:
        parser.error(f"Unknown source: {args.source}")
        return

    print(
        f"\nLoaded source documents: "
        f"{result['inserted']} inserted, "
        f"{result['updated']} updated, "
        f"{result['skipped']} skipped"
    )


_COMPANY_METADATA: dict[str, tuple[str, str]] = {
    "RELIANCE":   ("Reliance Industries Ltd.", "Energy"),
    "TCS":        ("Tata Consultancy Services Ltd.", "Information Technology"),
    "INFY":       ("Infosys Ltd.", "Information Technology"),
    "HDFCBANK":   ("HDFC Bank Ltd.", "Banking"),
    "ICICIBANK":  ("ICICI Bank Ltd.", "Banking"),
    "WIPRO":      ("Wipro Ltd.", "Information Technology"),
    "HINDUNILVR": ("Hindustan Unilever Ltd.", "FMCG"),
    "BAJFINANCE": ("Bajaj Finance Ltd.", "NBFC"),
    "SBIN":       ("State Bank of India", "Banking"),
    "LT":         ("Larsen & Toubro Ltd.", "Infrastructure"),
}


def _records_from_downloaded_pdfs(nse_dir: Path) -> list[DocumentRecord]:
    """Build DocumentRecords by scanning downloaded PDF paths.

    Filename convention: {TICKER}_{FINANCIAL_YEAR}_{DOCUMENT_TYPE}.pdf
    e.g. RELIANCE_FY2025_annual_report.pdf
    """
    records: list[DocumentRecord] = []
    for pdf in nse_dir.rglob("*.pdf"):
        parts = pdf.stem.split("_", 2)
        if len(parts) < 3:
            print(f"[WARN] Cannot parse filename: {pdf.name}")
            continue
        ticker, financial_year, document_type = parts[0], parts[1], parts[2]
        company_name, industry = _COMPANY_METADATA.get(ticker, (ticker, None))
        records.append(
            DocumentRecord(
                ticker=ticker,
                company_name=company_name,
                filing_date=datetime.now(UTC).date(),
                document_type=document_type,
                financial_year=financial_year,
                source="NSE",
                storage_path=pdf.resolve(),
                industry=industry,
            )
        )
    return records


if __name__ == "__main__":
    main()
