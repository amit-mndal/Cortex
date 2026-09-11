# from celery import Celery
# from app.core.config import settings

# celery_app = Celery(
#     "cortex",
#     broker=settings.redis_url,
#     backend=settings.redis_url,
# )

# celery_app.conf.update(
#     task_serializer="json",
#     result_serializer="json",
#     accept_content=["json"],
#     task_track_started=True,
# )


from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "cortex",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_use_ssl={
        "ssl_cert_reqs": "CERT_NONE",
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": "CERT_NONE",
    },
)