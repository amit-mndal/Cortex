import uuid
from pypdf import PdfReader
from app.core.config import settings
from app.retrieval.vector_store import add_chunks


def extract_pages(file_path: str) -> list[str]:
    if file_path.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        return [page.extract_text() or "" for page in reader.pages]
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return [f.read()]


def ingest_document(file_path: str, filename: str) -> dict:
    pages = extract_pages(file_path)
    doc_id = str(uuid.uuid4())
    all_chunks, all_pages = [], []

    for page_num, page_text in enumerate(pages, start=1):
        for chunk in chunk_text(page_text, settings.chunk_size, settings.chunk_overlap):
            all_chunks.append(chunk)
            all_pages.append(page_num)

    add_chunks(doc_id=doc_id, filename=filename, chunks=all_chunks, pages=all_pages)
    return {"doc_id": doc_id, "filename": filename, "num_chunks": len(all_chunks)}


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    chunks = []
    step = size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# def ingest_document(file_path: str, filename: str) -> dict:
#     text = extract_text(file_path)
#     chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
#     doc_id = str(uuid.uuid4())
#     add_chunks(doc_id=doc_id, filename=filename, chunks=chunks)
#     return {"doc_id": doc_id, "filename": filename, "num_chunks": len(chunks)}
