from __future__ import annotations

import pytest

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters, format_passages_for_agent

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("query", "filters", "expected_ticker"),
    [
        (
            "Infosys digital services constant currency growth",
            SearchFilters(ticker="INFY"),
            "INFY",
        ),
        (
            "Reliance retail growth Jio subscriber base",
            SearchFilters(ticker="RELIANCE"),
            "RELIANCE",
        ),
    ],
)
def test_retriever_returns_relevant_company_passages(
    query: str,
    filters: SearchFilters,
    expected_ticker: str,
) -> None:
    retriever = DocumentRetriever()
    passages = retriever.search(query, filters=filters, top_k=5)

    assert passages, f"No passages returned for query: {query!r}"
    assert all(p.ticker == expected_ticker for p in passages)

    combined = " ".join(p.text.lower() for p in passages)
    if expected_ticker == "INFY":
        assert any(term in combined for term in ("infosys", "revenue", "digital", "margin"))
    if expected_ticker == "RELIANCE":
        assert any(term in combined for term in ("retail", "jio", "revenue", "refinery", "oil"))

    formatted = format_passages_for_agent(passages)
    assert expected_ticker in formatted
    assert "[" in formatted
