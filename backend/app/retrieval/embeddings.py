"""Gemini query embedding for live retrieval."""

import time
from google import genai
from google.genai import types

from app.config import settings


def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def embed_query(text: str) -> list[float]:
    client = _client()
    expected_dims = settings.gemini_embedding_dimensions
    
    max_retries = 5
    delay = 2.0
    response = None
    
    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=expected_dims,
                )
            )
            break
        except Exception as exc:
            is_rate_limit = False
            if hasattr(exc, "status_code") and exc.status_code == 429:
                is_rate_limit = True
            elif "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                is_rate_limit = True
            
            if is_rate_limit and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2.0
            else:
                raise exc
                
    if not response or not response.embeddings:
        raise ValueError("No embeddings returned by Gemini API")
    
    embedding = response.embeddings[0].values
    if len(embedding) != expected_dims:
        raise ValueError(
            f"Expected embedding dimension {expected_dims}, got {len(embedding)}"
        )
    return embedding
