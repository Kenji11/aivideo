# Celery configuration
from celery import Celery
from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "video_generator",
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    # Include all task modules so Celery can discover them
    include=[
        "app.orchestrator.pipeline",
        "app.phases.phase1_validate.task",
        "app.phases.phase2_animatic.task",
        "app.phases.phase3_references.task",
    ],
)

# Import tasks to register them with Celery
# This ensures tasks are available when worker starts
from app.orchestrator import pipeline  # noqa: F401
from app.phases.phase1_validate import task as phase1_task  # noqa: F401
from app.phases.phase2_animatic import task as phase2_task  # noqa: F401
from app.phases.phase3_references import task as phase3_task  # noqa: F401
