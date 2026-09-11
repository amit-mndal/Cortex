"""
Local embedding model. Runs entirely on your machine - zero API cost,
zero rate limits. Uses a small, fast, high-quality sentence-transformer.

NOTE: the actual `sentence_transformers` import (which pulls in torch and
numpy) happens INSIDE get_embedder(), not at the top of this file. This is
deliberate: torch/numpy can fail to load on some Windows setups (DLL /
MinGW build conflicts), and if that import sat at module level, it would
crash the entire FastAPI app during startup - before /docs, before any
endpoint, before you'd get any useful error. Deferring it means the rest
of the API (health check, uploads, etc.) still comes up even if this one
piece is broken, and the real error surfaces when you actually hit an
endpoint that needs it - much easier to diagnose.
"""
from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    # Downloads once (~90MB), then cached locally forever.
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
