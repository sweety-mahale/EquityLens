"""LocalPdfSource — load PDFs from a local directory.

Simplest document source for manual corpus loading. Drop PDFs into a
directory with a companion ``manifest.json`` and this source will enumerate
them ready for ingestion.

manifest.json format:
[
  {
    "ticker": "RELIANCE",
    "company_name": "Reliance Industries Ltd.",
    "filing_date": "2025-05-30",
    "document_type": "annual_report",
    "financial_year": "FY2025",
    "industry": "Energy",
    "filename": "Reliance_FY2025_Annual_Report.pdf"
  }
]
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ingest.sources import DocumentRecord


class LocalPdfSource:
    """Enumerate PDFs in a directory described by a manifest.json file."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def fetch_documents(self) -> list[DocumentRecord]:
        manifest_path = self.directory / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"manifest.json not found in {self.directory}. "
                "Create a manifest.json listing the PDFs in this directory. "
                "See module docstring for the required format."
            )

        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        records: list[DocumentRecord] = []

        for entry in entries:
            pdf_path = self.directory / entry["filename"]
            if not pdf_path.is_file():
                raise FileNotFoundError(
                    f"PDF listed in manifest not found: {pdf_path}"
                )
            records.append(
                DocumentRecord(
                    ticker=entry["ticker"],
                    company_name=entry["company_name"],
                    filing_date=date.fromisoformat(entry["filing_date"]),
                    document_type=entry["document_type"],
                    financial_year=entry["financial_year"],
                    source=entry.get("source", "Company IR"),
                    storage_path=pdf_path.resolve(),
                    industry=entry.get("industry"),
                )
            )

        return records
