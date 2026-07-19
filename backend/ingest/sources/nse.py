"""NseDocumentSource — fetch corporate filings from NSE India.

Downloads Annual Reports and Quarterly Results from the NSE Corporate Filings
API for a given set of tickers.

Usage:
    from ingest.sources.nse import NseDocumentSource

    source = NseDocumentSource(
        tickers=["RELIANCE", "INFY", "TCS"],
        document_types=["annual_report", "quarterly_results"],
        output_dir=Path("data/nse_downloads"),
    )
    records = source.fetch_documents()

NSE API endpoints used:
  Annual Reports:        https://www.nseindia.com/api/annual-reports
  Quarterly Results:     https://www.nseindia.com/api/corporates-financial-results
"""

from __future__ import annotations

import re
import shutil
import time
import zipfile
from datetime import date
from pathlib import Path

import httpx

from ingest.sources import DocumentRecord

# Common headers for all NSE requests
_NSE_COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

_NSE_BASE = "https://www.nseindia.com"
_ANNUAL_REPORT_API = f"{_NSE_BASE}/api/annual-reports"
_QUARTERLY_API = f"{_NSE_BASE}/api/corporates-financial-results"

# Polite rate limit between requests (seconds)
_REQUEST_DELAY = 1.5


def _fy_from_date(d: date) -> str:
    """Convert a calendar date to Indian financial year string.

    Indian FY runs April → March.  A filing dated 2025-05-30 belongs to FY2025.
    """
    year = d.year if d.month >= 4 else d.year - 1
    return f"FY{year + 1}"


def _quarter_from_date(d: date) -> str:
    """Return the FY quarter label for a date, e.g. 'Q1FY26'."""
    month = d.month
    year = d.year
    if month >= 4 and month <= 6:
        quarter, fy = "Q1", year + 1
    elif month >= 7 and month <= 9:
        quarter, fy = "Q2", year + 1
    elif month >= 10 and month <= 12:
        quarter, fy = "Q3", year + 1
    else:
        quarter, fy = "Q4", year
    return f"{quarter}FY{fy}"


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-.]", "_", text)


class NseDocumentSource:
    """Download NSE corporate filings for a list of tickers.

    Args:
        tickers:        NSE symbol list, e.g. ["RELIANCE", "INFY", "TCS"].
        document_types: Subset of DocumentType values to fetch.
                        Supported: "annual_report", "quarterly_results".
        output_dir:     Directory to store downloaded PDFs.
        company_meta:   Optional dict mapping ticker → (company_name, industry).
        years:          If given, only download filings in these financial years
                        e.g. ["FY2023", "FY2024", "FY2025"].
    """

    def __init__(
        self,
        tickers: list[str],
        document_types: list[str] | None = None,
        output_dir: Path = Path("data/nse_downloads"),
        company_meta: dict[str, tuple[str, str | None]] | None = None,
        years: list[str] | None = None,
    ) -> None:
        self.tickers = [t.upper() for t in tickers]
        self.document_types = set(
            document_types or ["annual_report", "quarterly_results"]
        )
        self.output_dir = output_dir
        self.company_meta = company_meta or {}
        self.years = set(years) if years else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_documents(self) -> list[DocumentRecord]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        records: list[DocumentRecord] = []

        with httpx.Client(headers=_NSE_COMMON_HEADERS, follow_redirects=True, timeout=30) as client:
            # Warm the session cookie (NSE requires a browser session)
            _warm_session(client)

            for ticker in self.tickers:
                print(f"[NSE] Fetching filings for {ticker}...")
                if "annual_report" in self.document_types:
                    records.extend(self._fetch_annual_reports(client, ticker))
                if "quarterly_results" in self.document_types:
                    records.extend(self._fetch_quarterly_results(client, ticker))

        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_annual_reports(
        self, client: httpx.Client, ticker: str
    ) -> list[DocumentRecord]:
        try:
            api_headers = {
                "Accept": "application/json, text/plain, */*",
                "Referer": _NSE_BASE,
            }
            resp = client.get(
                _ANNUAL_REPORT_API,
                params={"symbol": ticker, "index": "cm"},
                headers=api_headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  [WARN] Annual reports API failed for {ticker}: {exc}")
            return []

        time.sleep(_REQUEST_DELAY)
        records: list[DocumentRecord] = []

        items = data.get("data", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        for item in items:
            pdf_url = item.get("fileName") or item.get("pdfLink", "")
            if not pdf_url:
                continue

            year_val = item.get("year") or item.get("fromYr") or item.get("toYr")
            if year_val:
                year_str = str(year_val).split("-")[0].strip()
                try:
                    start_year = int(year_str)
                    if start_year < 100:
                        start_year += 2000
                    fy = f"FY{start_year + 1}"
                except ValueError:
                    fy = "FY_UNKNOWN"
            else:
                fy = "FY_UNKNOWN"

            if self.years and fy not in self.years:
                continue

            filing_date_str = item.get("fromDate") or item.get("date") or item.get("broadcast_dttm")
            filing_date = _parse_nse_date(filing_date_str)

            record = self._download_and_build(
                client,
                ticker,
                pdf_url,
                document_type="annual_report",
                financial_year=fy,
                filing_date=filing_date,
            )
            if record:
                records.append(record)

        return records

    def _fetch_quarterly_results(
        self, client: httpx.Client, ticker: str
    ) -> list[DocumentRecord]:
        try:
            api_headers = {
                "Accept": "application/json, text/plain, */*",
                "Referer": _NSE_BASE,
            }
            resp = client.get(
                _QUARTERLY_API,
                params={"symbol": ticker, "corpType": "financial", "index": "equities"},
                headers=api_headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  [WARN] Quarterly results API failed for {ticker}: {exc}")
            return []

        time.sleep(_REQUEST_DELAY)
        records: list[DocumentRecord] = []

        items = data.get("data", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        for item in items:
            pdf_candidates = [
                item.get("pdfLink"),
                item.get("attachment"),
                item.get("resultDetailedDataLink"),
                item.get("xbrl"),
            ]
            pdf_url = next((url for url in pdf_candidates if url), "")
            if not pdf_url:
                continue

            filing_date_str = (
                item.get("dateOfSubmission")
                or item.get("date")
                or item.get("filingDate")
                or item.get("broadCastDate")
            )
            filing_date = _parse_nse_date(filing_date_str)
            if filing_date is None:
                continue

            fy = _quarter_from_date(filing_date)

            if self.years:
                base_fy = f"FY{fy[-4:]}"  # "FY2025" from "Q3FY2025"
                if base_fy not in self.years:
                    continue

            record = self._download_and_build(
                client,
                ticker,
                pdf_url,
                document_type="quarterly_results",
                financial_year=fy,
                filing_date=filing_date,
            )
            if record:
                records.append(record)

        return records

    def _download_and_build(
        self,
        client: httpx.Client,
        ticker: str,
        pdf_url: str,
        *,
        document_type: str,
        financial_year: str,
        filing_date: date | None,
    ) -> DocumentRecord | None:
        if not pdf_url:
            return None

        full_url = pdf_url if pdf_url.startswith("http") else f"{_NSE_BASE}{pdf_url}"
        filename = _safe_filename(f"{ticker}_{financial_year}_{document_type}.pdf")
        dest = self.output_dir / ticker / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.is_file():
            # If the file is already there, we might still need to extract it if it's a zip
            if zipfile.is_zipfile(dest):
                dest = _unzip_and_find_pdf(dest)
            else:
                print(f"  [SKIP] Already downloaded: {dest.name}")
        else:
            try:
                print(f"  [DOWN] {dest.name} ← {full_url}")
                pdf_resp = client.get(full_url)
                pdf_resp.raise_for_status()
                dest.write_bytes(pdf_resp.content)
                time.sleep(_REQUEST_DELAY)
                
                # Check if downloaded file is actually a zip (despite .pdf extension)
                if zipfile.is_zipfile(dest):
                    dest = _unzip_and_find_pdf(dest)
            except Exception as exc:
                print(f"  [WARN] Download failed for {full_url}: {exc}")
                return None

        company_name, industry = self.company_meta.get(ticker, (ticker, None))
        return DocumentRecord(
            ticker=ticker,
            company_name=company_name,
            filing_date=filing_date or date.today(),
            document_type=document_type,
            financial_year=financial_year,
            source="NSE",
            storage_path=dest.resolve(),
            industry=industry,
        )


def _unzip_and_find_pdf(zip_path: Path) -> Path:
    """Extract a ZIP archive (even if named with a .pdf extension) and return the path to the main PDF/HTML inside."""
    print(f"  [ZIP] Extracting zip file: {zip_path.name}...")
    temp_dir = zip_path.parent / f"_temp_extract_{zip_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # Find any PDF files inside
        pdfs = list(temp_dir.rglob("*.pdf"))
        if pdfs:
            # We copy the PDF to replace the original zip file path (which ends in .pdf)
            temp_pdf = zip_path.parent / f"_temp_{zip_path.name}"
            shutil.copy2(pdfs[0], temp_pdf)
            zip_path.unlink(missing_ok=True)
            temp_pdf.rename(zip_path)
            print(f"  [ZIP] Extracted PDF successfully: {zip_path.name}")
            return zip_path
            
        # If no PDF, look for HTML files
        htmls = list(temp_dir.rglob("*.html")) or list(temp_dir.rglob("*.htm"))
        if htmls:
            target_html = zip_path.with_suffix(".html")
            shutil.copy2(htmls[0], target_html)
            zip_path.unlink(missing_ok=True)
            print(f"  [ZIP] Extracted HTML file: {target_html.name}")
            return target_html
            
        # If no HTML, look for text files
        txts = list(temp_dir.rglob("*.txt"))
        if txts:
            target_txt = zip_path.with_suffix(".txt")
            shutil.copy2(txts[0], target_txt)
            zip_path.unlink(missing_ok=True)
            print(f"  [ZIP] Extracted TXT file: {target_txt.name}")
            return target_txt
            
    except Exception as e:
        print(f"  [WARN] Failed to extract zip archive {zip_path.name}: {e}")
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            
    return zip_path


def _parse_nse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _warm_session(client: httpx.Client) -> None:
    """Visit the NSE homepage to get a session cookie before API calls."""
    homepage_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    try:
        resp = client.get(_NSE_BASE, headers=homepage_headers, timeout=15)
        resp.raise_for_status()
        time.sleep(2)
    except Exception as exc:
        print(f"  [WARN] Failed to warm session: {exc}")
