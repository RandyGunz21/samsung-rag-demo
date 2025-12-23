"""Celery application configuration for async task processing."""

from celery import Celery
from .config import settings

# Create Celery app
celery_app = Celery(
    "rag-tester",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_track_started=settings.celery_task_track_started,
    task_time_limit=settings.celery_task_time_limit,
    result_expires=86400,  # Results expire after 24 hours
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (prevent memory leaks)
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["src"])
