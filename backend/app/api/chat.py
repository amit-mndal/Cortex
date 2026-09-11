import json
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.api.schemas import AskRequest, AskResponse, JobCreatedResponse
from app.agents.supervisor import run_supervisor
from app.core.progress import get_redis
from app.workers.tasks import run_agent_job

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    """Synchronous endpoint - blocks until the agent finishes. Kept for
    simplicity/testing; the frontend uses the async version below."""
    result = run_supervisor(payload.question)
    return result


@router.post("/ask-async", response_model=JobCreatedResponse)
def ask_async(payload: AskRequest):
    """Queues the agent run on a Celery worker and returns immediately.
    The frontend then opens /stream/{job_id} to watch live progress."""
    job_id = str(uuid.uuid4())
    run_agent_job.delay(job_id, payload.question)
    return {"job_id": job_id}


@router.get("/stream/{job_id}")
def stream(job_id: str):
    def event_generator():
        pubsub = get_redis().pubsub()
        pubsub.subscribe(f"job:{job_id}:progress")
        try:
            for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                if data["step"] == "end":
                    result = get_redis().get(f"job:{job_id}:result") or "{}"
                    yield f"event: result\ndata: {result}\n\n"
                    break
                yield f"event: progress\ndata: {json.dumps(data)}\n\n"
        finally:
            pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
