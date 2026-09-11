from rank_bm25 import BM25Okapi
from app.retrieval.vector_store import vector_search, get_all_chunks


def _bm25_search(query: str, top_k: int) -> list[dict]:
    corpus = get_all_chunks()
    if not corpus:
        return []
    tokenized_corpus = [c["text"].lower().split() for c in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(zip(corpus, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"text": c["text"], "metadata": c["metadata"], "score": float(s)} for c, s in ranked]


def _reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Merges multiple ranked lists into one, favoring items that rank
    highly across *multiple* retrieval methods (standard RRF formula)."""
    scores: dict[str, float] = {}
    lookup: dict[str, dict] = {}

    for results in result_lists:
        for rank, item in enumerate(results):
            key = item["text"]
            lookup[key] = item
            scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [lookup[key] for key, _ in fused]


def hybrid_retrieve(query: str, top_k: int = 5) -> list[dict]:
    vector_results = vector_search(query, top_k=top_k)
    keyword_results = _bm25_search(query, top_k=top_k)
    fused = _reciprocal_rank_fusion([vector_results, keyword_results])
    return fused[:top_k]
