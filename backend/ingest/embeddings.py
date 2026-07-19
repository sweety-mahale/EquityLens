"""Gemini embedding generation for document chunks."""

from __future__ import annotations

import time
from google import genai
from google.genai import types

from app.config import settings

EMBED_BATCH_SIZE = 100


def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def embed_texts(texts: list[str], *, batch_size: int = EMBED_BATCH_SIZE) -> list[list[float]]:
    if not texts:
        return []

    client = _client()
    expected_dims = settings.gemini_embedding_dimensions
    vectors: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        
        # Wrap each text in types.Content to ensure correct batch processing
        contents = [types.Content(parts=[types.Part(text=s)]) for s in batch]
        
        max_retries = 5
        delay = 2.0
        response = None
        
        for attempt in range(max_retries):
            try:
                response = client.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=contents,
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
                    print(f"  [WARN] Rate limit hit. Sleeping {delay}s before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    delay *= 2.0  # Exponential backoff
                else:
                    raise exc
        
        if not response or not response.embeddings:
            raise ValueError("No embeddings returned by Gemini API")
            
        for item in response.embeddings:
            embedding = item.values
            if len(embedding) != expected_dims:
                raise ValueError(
                    f"Expected embedding dimension {expected_dims}, got {len(embedding)}"
                )
            vectors.append(embedding)

    return vectors
