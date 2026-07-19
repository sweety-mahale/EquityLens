import enum

# Must match `gemini_embedding_dimensions` in config and the Alembic migration.
EMBEDDING_DIMENSIONS = 768


class DocumentType(str, enum.Enum):
    """Controlled vocabulary for Indian corporate filing types."""

    annual_report = "annual_report"
    quarterly_results = "quarterly_results"
    investor_presentation = "investor_presentation"
    earnings_call = "earnings_call"
    corporate_announcement = "corporate_announcement"
