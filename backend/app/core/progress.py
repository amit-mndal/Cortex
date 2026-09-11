import json
import redis
from app.core.config import settings

_redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis.Redis:
    return _redis_client


def publish_progress(job_id: str, step: str, message: str) -> None:
    """Broadcasts a progress update for a running job. The /stream/{job_id}
    SSE endpoint is subscribed to this channel and relays it to the browser
    in real time."""
    if not job_id:
        return
    payload = json.dumps({"step": step, "message": message})
    _redis_client.publish(f"job:{job_id}:progress", payload)


def end_job(job_id: str) -> None:
    _redis_client.publish(f"job:{job_id}:progress", json.dumps({"step": "end", "message": "done"}))
