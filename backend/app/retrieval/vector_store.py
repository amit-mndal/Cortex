import chromadb
from app.core.config import settings
from app.retrieval.embeddings import embed_texts, embed_query

_client = chromadb.PersistentClient(path=settings.chroma_db_path)
_collection = _client.get_or_create_collection(name=settings.collection_name)


def add_chunks(doc_id: str, filename: str, chunks: list[str], pages: list[int] | None = None) -> None:
    ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
    embeddings = embed_texts(chunks)
    metadatas = [
        {
            "filename": filename,
            "doc_id": doc_id,
            "chunk_index": i,
            "page": pages[i] if pages else 1,
        }
        for i in range(len(chunks))
    ]
    _collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)


def vector_search(query: str, top_k: int = 5) -> list[dict]:
    if _collection.count() == 0:
        return []

    query_vec = embed_query(query)
    results = _collection.query(query_embeddings=[query_vec], n_results=top_k)

    if not results.get("documents") or not results["documents"][0]:
        return []

    return [
        {"text": doc, "metadata": meta, "score": 1 - dist}
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]


# def get_all_chunks() -> list[dict]:
#     """Used to build the BM25 keyword index alongside vector search."""
#     data = _collection.get()
#     return [
#         {"text": doc, "metadata": meta}
#         for doc, meta in zip(data["documents"], data["metadatas"])
#     ]


def get_all_chunks() -> list[dict]:
    """Used to build the BM25 keyword index alongside vector search."""
    if _collection.count() == 0:
        return []
    data = _collection.get()
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []
    return [{"text": doc, "metadata": meta} for doc, meta in zip(documents, metadatas)]


def has_documents() -> bool:
    return _collection.count() > 0




def delete_document(doc_id: str) -> None:
    _collection.delete(where={"doc_id": doc_id})