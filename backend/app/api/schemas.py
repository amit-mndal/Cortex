from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    index: int
    filename: str
    page: int | None = None 
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    retries: int
    route: str


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    num_chunks: int


class JobCreatedResponse(BaseModel):
    job_id: str
