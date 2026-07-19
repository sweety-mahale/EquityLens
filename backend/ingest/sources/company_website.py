"""CompanyWebsiteSource — scrape PDF links from a company IR page.

This source is for companies that publish filings on their own investor
relations websites rather than (or in addition to) NSE.

Usage:
    from ingest.sources.company_website import CompanyWebsiteSource

    source = CompanyWebsiteSource(
        companies=[
            {
                "ticker": "HDFCBANK",
                "company_name": "HDFC Bank Ltd.",
                "industry": "Banking",
                "ir_url": "https://www.hdfcbank.com/content/bbp/repositories/...",
                "document_type": "annual_report",
                "financial_year": "FY2025",
                "filing_date": "2025-06-10",
            }
        ],
        output_dir=Path("data/company_downloads"),
    )
    records = source.fetch_documents()
"""

from __future__ import annotations

import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from ingest.sources import DocumentRecord

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
}
_REQUEST_DELAY = 1.5


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-.]", "_", text)


class CompanyWebsiteSource:
    """Download PDFs from company investor relations pages.

    For each entry in ``companies``:
    - If ``pdf_url`` is provided directly, download it.
    - Otherwise scrape ``ir_url`` looking for the first PDF link.
    """

    def __init__(
        self,
        companies: list[dict],
        output_dir: Path = Path("data/company_downloads"),
    ) -> None:
        self.companies = companies
        self.output_dir = output_dir

    def fetch_documents(self) -> list[DocumentRecord]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        records: list[DocumentRecord] = []

        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
            for entry in self.companies:
                record = self._process_entry(client, entry)
                if record:
                    records.append(record)

        return records

    def _process_entry(
        self, client: httpx.Client, entry: dict
    ) -> DocumentRecord | None:
        ticker = entry["ticker"]
        pdf_url = entry.get("pdf_url") or self._find_pdf_url(client, entry.get("ir_url", ""))

        if not pdf_url:
            print(f"  [WARN] No PDF URL found for {ticker}")
            return None

        filename = _safe_filename(
            f"{ticker}_{entry.get('financial_year', 'UNKNOWN')}_{entry.get('document_type', 'doc')}.pdf"
        )
        dest = self.output_dir / ticker / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.is_file():
            print(f"  [SKIP] Already downloaded: {dest.name}")
        else:
            try:
                print(f"  [DOWN] {dest.name} ← {pdf_url}")
                resp = client.get(pdf_url)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                time.sleep(_REQUEST_DELAY)
            except Exception as exc:
                print(f"  [WARN] Download failed: {exc}")
                return None

        filing_date_str = entry.get("filing_date")
        filing_date = date.fromisoformat(filing_date_str) if filing_date_str else date.today()

        return DocumentRecord(
            ticker=ticker,
            company_name=entry.get("company_name", ticker),
            filing_date=filing_date,
            document_type=entry.get("document_type", "annual_report"),
            financial_year=entry.get("financial_year", "FY_UNKNOWN"),
            source=entry.get("source", "Company IR"),
            storage_path=dest.resolve(),
            industry=entry.get("industry"),
        )

    def _find_pdf_url(self, client: httpx.Client, ir_url: str) -> str | None:
        """Scrape the first PDF link from an IR page."""
        if not ir_url:
            return None
        try:
            resp = client.get(ir_url, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            print(f"  [WARN] Could not fetch IR page {ir_url}: {exc}")
            return None

        # Find all href values ending in .pdf (case-insensitive)
        pdf_links = re.findall(r'href=["\']([^"\']+\.pdf)["\']', resp.text, re.IGNORECASE)
        if not pdf_links:
            return None

        base = f"{urlparse(ir_url).scheme}://{urlparse(ir_url).netloc}"
        return urljoin(base, pdf_links[0])
