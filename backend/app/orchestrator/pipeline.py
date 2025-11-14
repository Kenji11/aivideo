# Main orchestration task
from app.orchestrator.celery_app import celery_app

@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: list):
    """
    Main orchestration task - chains all 6 phases sequentially.
    Each person implements their phase tasks independently.
    """
    # TODO: Implement full pipeline orchestration
    # This will chain Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6
    pass
