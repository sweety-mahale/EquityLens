import asyncio
import uuid

import pytest

from app.assistant.agent import run_document_agent
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.grounding.validator import GroundingValidator
from app.retrieval.retriever import DocumentRetriever


@pytest.mark.integration
def test_agent_answers_infosys_question_with_citations() -> None:
    registry = TurnRegistry()
    deps = DocumentAgentDeps(
        retriever=DocumentRetriever(),
        registry=registry,
        thread_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )
    answer = run_document_agent(
        "How did Infosys describe digital services revenue in its recent annual reports?",
        deps,
    )
    validation = asyncio.run(GroundingValidator().validate(answer, registry))

    assert validation.ok
    if not answer.insufficient_evidence:
        assert answer.citations
        tickers = {
            registry.passages_by_chunk_id[c.chunk_id].ticker
            for c in answer.citations
        }
        assert "INFY" in tickers


@pytest.mark.integration
def test_agent_refuses_underspecified_stock_pick_question() -> None:
    registry = TurnRegistry()
    deps = DocumentAgentDeps(
        retriever=DocumentRetriever(),
        registry=registry,
        thread_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )
    answer = run_document_agent("What is the best stock to buy right now?", deps)
    validation = asyncio.run(GroundingValidator().validate(answer, registry))

    assert validation.ok
    assert answer.insufficient_evidence or not answer.citations
