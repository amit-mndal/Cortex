"""
Semantic cache: stores past (question, answer) pairs by embedding.
Before running the full multi-agent pipeline, check if a highly similar
question was already answered - if so, skip the agent run entirely and
return the cached answer in milliseconds instead of seconds.

Uses a dedicated ChromaDB collection so it doesn't mix with the document
index used for RAG retrieval.
"""
import json
import time
import uuid
import chromadb
from app.core.config import settings
from app.retrieval.embeddings import embed_query

SIMILARITY_THRESHOLD = 0.93  # cosine similarity; tune higher = stricter match
CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 hours

_client = chromadb.PersistentClient(path=settings.chroma_db_path)
_cache_collection = _client.get_or_create_collection(name="semantic_cache")


def check_cache(question: str) -> dict | None:
    if _cache_collection.count() == 0:
        return None

    query_vec = embed_query(question)
    results = _cache_collection.query(query_embeddings=[query_vec], n_results=1)

    if not results.get("ids") or not results["ids"][0]:
        return None
    if not results.get("distances") or not results["distances"][0]:
        return None
    if not results.get("metadatas") or not results["metadatas"][0]:
        return None

    distance = results["distances"][0][0]
    similarity = 1 - distance
    if similarity < SIMILARITY_THRESHOLD:
        return None

    metadata = results["metadatas"][0][0]
    if time.time() - metadata["cached_at"] > CACHE_TTL_SECONDS:
        return None

    return json.loads(metadata["result_json"])

def store_cache(question: str, result: dict) -> None:
    query_vec = embed_query(question)
    _cache_collection.add(
        ids=[str(uuid.uuid4())],
        embeddings=[query_vec],
        documents=[question],
        metadatas=[{"result_json": json.dumps(result), "cached_at": time.time()}],
    )


def clear_cache() -> None:
    """Wipes the semantic cache. Called whenever documents change, since
    old cached answers may no longer be valid against the new knowledge base."""
    global _cache_collection
    _client.delete_collection(name="semantic_cache")
    _cache_collection = _client.get_or_create_collection(name="semantic_cache")