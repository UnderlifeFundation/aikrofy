"""
Celery Application Factory — Phase 11: Enterprise Scale.
Provides async task execution for heavy operations (PDF, RAG, Broadcasts).

Usage:
    # Start worker:
    celery -A celery_app.celery worker --loglevel=info

Migration Path: Task queue will transition to a P2P job mesh.
"""
import os
import logging
from celery import Celery
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger(__name__)


def make_celery(app=None):
    """Create a Celery instance tied to the application context."""
    broker = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6380/0')
    backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6380/1')

    celery = Celery(
        'aikrofy',
        broker=broker,
        backend=backend,
        include=['tasks']  # Auto-discover tasks module
    )

    celery.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,              # Requeue on worker crash
        worker_prefetch_multiplier=1,     # Fair scheduling
        broker_connection_retry_on_startup=True,
    )

    if app:
        celery.conf.update(app.config)

    # Configure Periodic Tasks (Celery Beat)
    from celery.schedules import crontab
    celery.conf.beat_schedule = {
        'reset-monthly-credits-daily': {
            'task': 'tasks.reset_monthly_credits',
            'schedule': crontab(hour=0, minute=0),  # Run daily at midnight UTC
        },
        'lead-score-decay-daily': {
            'task': 'tasks.lead_score_decay_task',
            'schedule': crontab(hour=1, minute=0),  # Run daily at 1:00 AM UTC
        },
        'cleanup-voice-files-daily': {
            'task': 'tasks.cleanup_voice_files',
            'schedule': crontab(hour=2, minute=0),  # Run daily at 2:00 AM UTC
        },
        'autonomous-consciousness-pulse': {
            'task': 'tasks.autonomous_pulse_check',
            'schedule': 900.0,  # Run every 15 minutes (deterministic, zero LLM token cost)
        },
    }

    if app:
        class ContextTask(celery.Task):
            """Ensure Flask app context is available inside tasks."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Default instance (can be used without Flask for worker startup)
celery = make_celery()


# ── Celery Task Database Connection Cleanup ───────────────────────────────────
from celery.signals import task_postrun

@task_postrun.connect
def close_db_session(sender, **kwargs):
    """
    Ensure database connections are released/returned to the pool after each Celery task finishes.
    This prevents connection leaks and 'MySQL server has gone away' issues in Celery background workers.
    """
    try:
        from database import db_session
        db_session.remove()
    except Exception as e:
        logger.warning(f"Error removing db_session in task_postrun: {e}")
# ─────────────────────────────────────────────────────────────────────────────

