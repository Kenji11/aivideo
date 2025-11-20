# Celery configuration
import logging
from celery import Celery
from app.config import get_settings

logger = logging.getLogger(__name__)

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
        "app.phases.phase1_validate.task_intelligent",
        "app.phases.phase2_storyboard.task",
        "app.phases.phase3_chunks.task",
        "app.phases.phase4_refine.task",
    ],
)

# Import tasks to register them with Celery
# This ensures tasks are available when worker starts
logger.info("Importing task modules...")
try:
    from app.orchestrator import pipeline  # noqa: F401
    logger.info("✓ Imported app.orchestrator.pipeline")
except Exception as e:
    logger.error(f"✗ Failed to import app.orchestrator.pipeline: {e}", exc_info=True)
    raise

try:
    from app.phases.phase1_validate import task_intelligent as phase1_task  # noqa: F401
    logger.info("✓ Imported app.phases.phase1_validate.task_intelligent")
except Exception as e:
    logger.error(f"✗ Failed to import app.phases.phase1_validate.task_intelligent: {e}", exc_info=True)
    raise

try:
    from app.phases.phase2_storyboard import task as phase2_task  # noqa: F401
    logger.info("✓ Imported app.phases.phase2_storyboard.task")
except Exception as e:
    logger.error(f"✗ Failed to import app.phases.phase2_storyboard.task: {e}", exc_info=True)
    raise

try:
    from app.phases.phase3_chunks import task as phase3_task  # noqa: F401
    logger.info("✓ Imported app.phases.phase3_chunks.task")
except Exception as e:
    logger.error(f"✗ Failed to import app.phases.phase3_chunks.task: {e}", exc_info=True)
    raise

try:
    from app.phases.phase4_refine import task as phase4_task  # noqa: F401
    logger.info("✓ Imported app.phases.phase4_refine.task")
except Exception as e:
    logger.error(f"✗ Failed to import app.phases.phase4_refine.task: {e}", exc_info=True)
    raise

logger.info("All task modules imported successfully")
