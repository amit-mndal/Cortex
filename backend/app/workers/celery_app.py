import ssl
from celery import Celery
from app.core.config import settings


def _with_ssl_param(url: str) -> str:
    """Celery/Kombu's redis transport needs ssl_cert_reqs as a URL query
    param for rediss:// URLs (Upstash, Heroku Redis, etc.) - setting it
    only via broker_use_ssl config is unreliable across Kombu versions."""
    if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}ssl_cert_reqs=CERT_NONE"
    return url


_redis_url = _with_ssl_param(settings.redis_url)

celery_app = Celery(
    "cortex",
    broker=_redis_url,
    backend=_redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
    redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
)