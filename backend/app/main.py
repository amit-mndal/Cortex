from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import chat, documents, evals
from app.db.session import init_db

app = FastAPI(title="Cortex API", version="0.1.0")

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(evals.router, prefix="/api", tags=["evals"])


@app.get("/health")
def health():
    return {"status": "ok"}
