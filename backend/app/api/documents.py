import os
import shutil
from fastapi import APIRouter, UploadFile, File
from app.api.schemas import UploadResponse
from app.retrieval.ingest import ingest_document
from app.retrieval.vector_store import delete_document
from app.cache.semantic_cache import clear_cache

router = APIRouter()
UPLOAD_DIR = "./data/uploads"
CSV_DIR = "./data/csvs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    # CSVs go to the Data-Analysis agent's folder (read directly with pandas,
    # not chunked/embedded - a spreadsheet isn't semantic text).
    if file.filename.lower().endswith(".csv"):
        dest_path = os.path.join(CSV_DIR, file.filename)
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"doc_id": file.filename, "filename": file.filename, "num_chunks": 0}

    # PDFs/txt go through the normal RAG ingestion pipeline.
    dest_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = ingest_document(dest_path, file.filename)
    return result





@router.delete("/documents/{doc_id}")
async def delete(doc_id: str):
    # CSVs are stored as plain files named by the doc_id (see upload() above)
    csv_path = os.path.join(CSV_DIR, doc_id)
    if os.path.exists(csv_path):
        os.remove(csv_path)
        return {"deleted": doc_id}

    delete_document(doc_id)
    return {"deleted": doc_id}
