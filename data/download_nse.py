#!/usr/bin/env python
"""Download Indian corporate filings from NSE for the India Financials Copilot.

Edit the COMPANIES list and TARGET_FYS below, then run:

    uv run data/download_nse.py

Downloaded PDFs land in data/nse_downloads/<TICKER>/.
Run convert and ingest steps after downloading:

    cd backend
    uv run python -m ingest.load_source_documents --source nse
    uv run python -m ingest.chunk_and_embed --all
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG — edit these before running
# ---------------------------------------------------------------------------

COMPANIES: list[dict] = [
    {"ticker": "RELIANCE",   "company_name": "Reliance Industries Ltd.",   "industry": "Energy"},
    {"ticker": "INFY",       "company_name": "Infosys Ltd.",                "industry": "Information Technology"},
    {"ticker": "TCS",        "company_name": "Tata Consultancy Services Ltd.", "industry": "Information Technology"},
    {"ticker": "HDFCBANK",   "company_name": "HDFC Bank Ltd.",              "industry": "Banking"},
    {"ticker": "ICICIBANK",  "company_name": "ICICI Bank Ltd.",             "industry": "Banking"},
    {"ticker": "WIPRO",      "company_name": "Wipro Ltd.",                  "industry": "Information Technology"},
    {"ticker": "HINDUNILVR", "company_name": "Hindustan Unilever Ltd.",     "industry": "FMCG"},
    {"ticker": "BAJFINANCE", "company_name": "Bajaj Finance Ltd.",          "industry": "NBFC"},
]

DOCUMENT_TYPES: list[str] = ["annual_report", "quarterly_results"]

# Which financial years to download.  Set to None to download all available.
TARGET_FYS: list[str] | None = ["FY2022", "FY2023", "FY2024", "FY2025"]

OUTPUT_DIR = Path(__file__).resolve().parent / "nse_downloads"

# ---------------------------------------------------------------------------

def main() -> None:
    # Add backend to path so ingest.sources is importable
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    sys.path.insert(0, str(backend_dir))

    from ingest.sources.nse import NseDocumentSource  # noqa: PLC0415

    company_meta = {
        entry["ticker"]: (entry["company_name"], entry.get("industry"))
        for entry in COMPANIES
    }

    source = NseDocumentSource(
        tickers=[entry["ticker"] for entry in COMPANIES],
        document_types=DOCUMENT_TYPES,
        output_dir=OUTPUT_DIR,
        company_meta=company_meta,
        years=TARGET_FYS,
    )

    print(f"Downloading filings to: {OUTPUT_DIR}")
    records = source.fetch_documents()

    print(f"\n✓ Fetched {len(records)} filing(s):")
    for r in records:
        print(f"  {r.ticker:12s}  {r.financial_year:8s}  {r.document_type:30s}  {r.storage_path.name}")


if __name__ == "__main__":
    main()
