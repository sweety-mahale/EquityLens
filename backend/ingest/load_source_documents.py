"""Load corporate filings from any DocumentSource into source_documents.

Supports Indian corporate filings (NSE, Company IR) and the legacy SEC corpus.
The pipeline is source-agnostic: any class implementing the DocumentSource
protocol can be used.

Usage (NSE):
    uv run python -m ingest.load_source_documents --source nse

Usage (local PDFs):
    uv run python -m ingest.load_source_documents --source local --dir data/my_pdfs

Usage (legacy SEC manifest, unchanged behavior):
    uv run python -m ingest.load_source_documents --source sec
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
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
    ``markdown_content`` yet.  Skips existing rows by (ticker, financial_year,
    document_type) key.
    """
    engine = create_engine(settings.sqlalchemy_database_url)
    counts = {"inserted": 0, "skipped": 0, "updated": 0}

    with Session(engine) as session:
        existing_keys = _existing_india_docs(session)

        for record in records:
            key = _india_key(record)

            if SKIP_EXISTING and key in existing_keys:
                print(f"Skipping existing {record.ticker} {record.financial_year} {record.document_type}")
                counts["skipped"] += 1
                continue

            # Convert PDF → Markdown if needed
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

            if key in existing_keys:
                # Update path
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
                    counts["updated"] += 1
                    print(f"Updated {record.ticker} {record.financial_year}")
            else:
                session.add(SourceDocument(**fields))
                counts["inserted"] += 1
                print(f"Inserted {record.ticker} {record.financial_year} {record.document_type}")

        session.commit()

    return counts


# ---------------------------------------------------------------------------
# Legacy SEC loader (preserved for backward compatibility)
# ---------------------------------------------------------------------------

_SEC_COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}

_SEC_DOC_TYPE_MAP = {
    "10-K": "annual_report",
    "10-Q": "quarterly_results",
}


def _load_sec_manifest(markdown_dir: Path) -> dict[str, int]:
    """Load legacy SEC manifest.json (original behavior preserved)."""
    manifest_path = markdown_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Missing {manifest_path}. Run `uv run data/convert_to_markdown.py` first."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    filings = manifest.get("filings", [])

    engine = create_engine(settings.sqlalchemy_database_url)
    counts = {"inserted": 0, "skipped": 0, "updated": 0}

    with Session(engine) as session:
        for filing in filings:
            accession_number = filing["accession_number"]
            existing = session.scalar(
                select(SourceDocument).where(
                    SourceDocument.accession_number == accession_number
                )
            )

            if existing and SKIP_EXISTING:
                print(f"Skipping existing {accession_number}")
                counts["skipped"] += 1
                continue

            markdown_path = markdown_dir / filing["local_path"]
            if not markdown_path.is_file():
                raise FileNotFoundError(f"Missing Markdown file: {markdown_path}")

            form = filing.get("form", "")
            fiscal_year_int = int(filing.get("report_date", "")[:4]) if filing.get("report_date") else None

            fields = {
                "ticker": filing["ticker"],
                "cik": filing["cik"],
                "company_name": _SEC_COMPANY_NAMES.get(filing["ticker"]),
                "form": form,
                "filing_date": date.fromisoformat(filing["filing_date"]) if filing.get("filing_date") else date.today(),
                "report_date": date.fromisoformat(filing["report_date"]) if filing.get("report_date") else None,
                "fiscal_year": fiscal_year_int,
                "accession_number": accession_number,
                "primary_document": filing["primary_document"],
                "source_url": filing["source_url"],
                "markdown_content": markdown_path.read_text(encoding="utf-8"),
                "ingested_at": datetime.now(UTC),
                # Map SEC form types to the new document_type vocabulary
                "document_type": _SEC_DOC_TYPE_MAP.get(form),
                "financial_year": f"FY{fiscal_year_int}" if fiscal_year_int else None,
                "source": "SEC EDGAR",
            }

            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
                counts["updated"] += 1
                print(f"Updating {accession_number}...")
            else:
                session.add(SourceDocument(**fields))
                counts["inserted"] += 1
                print(f"Inserting {accession_number}...")

        session.commit()

    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["nse", "local", "sec"],
        default="sec",
        help="Document source to load (default: sec)",
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

    if args.source == "sec":
        markdown_dir = Path(__file__).resolve().parents[2] / "data" / "markdown"
        result = _load_sec_manifest(markdown_dir)

    elif args.source == "nse":
        from ingest.sources.nse import NseDocumentSource  # noqa: PLC0415

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


def _records_from_downloaded_pdfs(nse_dir: Path) -> list[DocumentRecord]:
    """Build DocumentRecords by scanning downloaded PDF paths.

    Filename convention: {TICKER}_{FINANCIAL_YEAR}_{DOCUMENT_TYPE}.pdf
    e.g. RELIANCE_FY2025_annual_report.pdf
    """
    import re

    records: list[DocumentRecord] = []
    for pdf in nse_dir.rglob("*.pdf"):
        parts = pdf.stem.split("_", 2)
        if len(parts) < 3:
            print(f"[WARN] Cannot parse filename: {pdf.name}")
            continue
        ticker, financial_year, document_type = parts[0], parts[1], parts[2]
        records.append(
            DocumentRecord(
                ticker=ticker,
                company_name=ticker,
                filing_date=datetime.now(UTC).date(),
                document_type=document_type,
                financial_year=financial_year,
                source="NSE",
                storage_path=pdf.resolve(),
            )
        )
    return records


if __name__ == "__main__":
    main()
