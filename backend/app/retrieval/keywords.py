"""LLM keyword extraction for Postgres full-text search."""

from __future__ import annotations

import re

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config import settings
from app.retrieval.types import SearchFilters

_FILLER_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "across",
        "are",
        "as",
        "at",
        "be",
        "between",
        "by",
        "change",
        "changed",
        "describe",
        "describes",
        "described",
        "did",
        "do",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "its",
        "of",
        "on",
        "or",
        "the",
        "their",
        "they",
        "this",
        "to",
        "was",
        "way",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
        "was",
    }
)

_LOW_VALUE_FTS_WORDS = frozenset(
    {
        "driver",
        "drivers",
        "describe",
        "described",
        "describes",
        "change",
        "changed",
        "across",
        "way",
        "ks",
        "k",
    }
)

_KNOWN_PHRASES = (
    # Indian corporate finance phrases
    "revenue mix",
    "operating margin",
    "net profit",
    "ebitda margin",
    "return on equity",
    "capital expenditure",
    "earnings per share",
    "dividend payout",
    "free cash flow",
    "debt equity ratio",
    "working capital",
    "annual report",
    "quarterly results",
    "investor presentation",
    "corporate announcement",
    "management discussion",
    "risk factors",
    # Tech / sector phrases
    "cloud revenue",
    "data center",
    "customer concentration",
    "supply chain",
    "ai infrastructure",
    "digital transformation",
)

# NSE ticker → lowercase company name prefix (used to suppress company name
# from FTS keywords when a ticker filter is already applied)
_TICKER_COMPANY_PREFIXES: dict[str, str] = {
    # Large-cap Indian companies
    "RELIANCE": "reliance",
    "INFY": "infosys",
    "TCS": "tata",
    "HDFCBANK": "hdfc",
    "ICICIBANK": "icici",
    "WIPRO": "wipro",
    "HINDUNILVR": "hindustan",
    "BAJFINANCE": "bajaj",
    "KOTAKBANK": "kotak",
    "SBIN": "state",
    "TATAMOTORS": "tata",
    "ADANIPORTS": "adani",
    "SUNPHARMA": "sun",
    "ONGC": "ongc",
    "NTPC": "ntpc",
    # Legacy SEC tickers (preserved for backward compat)
    "AAPL": "apple",
    "AMZN": "amazon",
    "GOOGL": "google",
    "MSFT": "microsoft",
    "NVDA": "nvidia",
}

_SYSTEM_PROMPT = """\
You extract search keywords for PostgreSQL full-text search over Indian corporate filing chunks.

Rules:
- Return 3 to 5 terms. When joined with spaces, the total word count must be 5 or fewer \
(PostgreSQL ANDs every word — extra words cause zero matches).
- Prefer domain nouns and standard Indian financial/corporate phrases \
(e.g. "ebitda margin", "revenue mix", "capital expenditure", "annual report").
  Each multi-word phrase counts toward the word limit.
- Omit question filler and generic verbs (how, what, describe, change, drivers, across).
- Preserve product-name and company-name casing from the query.
- Recognise Indian financial year notation: FY2025, Q3FY24, H1FY23.
- When a ticker filter is provided, omit the company name from terms.
"""


class FtsKeywordExtraction(BaseModel):
    terms: list[str] = Field(
        min_length=1,
        description="3-5 search terms for full-text search",
    )


def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _token_count(query: str) -> int:
    return len(query.split())


def _normalize_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for term in terms:
        cleaned = term.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _is_company_token(token: str, filters: SearchFilters | None) -> bool:
    if filters is None or (filters.ticker is None and not filters.tickers):
        return False
    
    resolved_tickers = []
    if filters.tickers:
        resolved_tickers = [t.upper() for t in filters.tickers]
    elif filters.ticker:
        resolved_tickers = [filters.ticker.upper()]
        
    for t in resolved_tickers:
        prefix = _TICKER_COMPANY_PREFIXES.get(t)
        if prefix and token.casefold().startswith(prefix):
            return True
    return False


def _phrases_in_query(query: str) -> list[str]:
    lowered = query.casefold()
    found: list[str] = []
    for phrase in _KNOWN_PHRASES:
        start = lowered.find(phrase)
        if start == -1:
            continue
        found.append(query[start : start + len(phrase)])
    return found


def _capitalized_tokens(query: str, *, filters: SearchFilters | None) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9]*(?:'s)?", query)
    caps: list[str] = []
    for token in tokens:
        bare = token.removesuffix("'s")
        if bare.casefold() in _FILLER_WORDS:
            continue
        if bare.casefold() in _LOW_VALUE_FTS_WORDS:
            continue
        if _is_company_token(token, filters):
            continue
        if len(bare) <= 2:
            continue
        if bare[0].isupper() or re.fullmatch(r"i[A-Z][A-Za-z0-9]*", bare):
            caps.append(bare)
    return caps


def _apply_word_budget(words: list[str]) -> list[str]:
    maximum = settings.retrieval_fts_keyword_max
    seen: set[str] = set()
    kept: list[str] = []
    for word in words:
        for part in word.split():
            key = part.casefold()
            if key in seen:
                continue
            if key in _FILLER_WORDS or key in _LOW_VALUE_FTS_WORDS:
                continue
            seen.add(key)
            kept.append(part)
            if len(kept) >= maximum:
                return kept
    return kept


def _merge_fts_words(
    query: str,
    llm_terms: list[str],
    *,
    filters: SearchFilters | None,
) -> list[str]:
    caps = _capitalized_tokens(query, filters=filters)
    phrases = _phrases_in_query(query)
    llm_words = _apply_word_budget(_flatten_term_list(llm_terms))

    candidates: list[str] = []
    if len(caps) >= 3:
        candidates.extend(caps)
    else:
        candidates.extend(phrases)
        candidates.extend(caps)
    candidates.extend(llm_words)
    return _apply_word_budget(candidates)


def _flatten_term_list(terms: list[str]) -> list[str]:
    words: list[str] = []
    for term in terms:
        words.extend(term.split())
    return words


def _deterministic_fallback(query: str, *, filters: SearchFilters | None) -> str:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/]*", query)
    kept: list[str] = []
    for token in tokens:
        if token.casefold() in _FILLER_WORDS:
            continue
        if _is_company_token(token, filters):
            continue
        kept.append(token)
    words = _merge_fts_words(query, kept, filters=filters)
    if not words:
        return query.strip()
    return " ".join(words)


def _build_user_message(query: str, filters: SearchFilters | None) -> str:
    parts = [f"Query: {query}"]
    
    resolved_tickers = []
    if filters:
        if filters.tickers:
            resolved_tickers = filters.tickers
        elif filters.ticker:
            resolved_tickers = [filters.ticker]
            
    if resolved_tickers:
        parts.append(f"Ticker filters: {', '.join(resolved_tickers)} (omit company names from terms)")
    if filters is not None and filters.form is not None:
        parts.append(f"Form filter: {filters.form}")
    return "\n".join(parts)


def extract_fts_keywords(
    query: str,
    *,
    filters: SearchFilters | None = None,
) -> str:
    """Return a space-joined keyword string for plainto_tsquery."""
    stripped = query.strip()
    if not stripped:
        return stripped

    if _token_count(stripped) <= settings.retrieval_fts_keyword_fast_path_tokens:
        return stripped

    try:
        client = _client()
        response = client.models.generate_content(
            model=settings.retrieval_fts_keyword_model,
            contents=_build_user_message(stripped, filters),
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=FtsKeywordExtraction,
                temperature=0.0,
            ),
        )
        parsed = response.parsed
        if parsed is None:
            return _deterministic_fallback(stripped, filters=filters)

        words = _merge_fts_words(stripped, _normalize_terms(parsed.terms), filters=filters)
        if len(words) < settings.retrieval_fts_keyword_min:
            return _deterministic_fallback(stripped, filters=filters)
        return " ".join(words)
    except Exception:
        return _deterministic_fallback(stripped, filters=filters)
